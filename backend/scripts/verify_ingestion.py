#!/usr/bin/env python3
"""ProfitMax Ingestion Verification Suite (`verify_ingestion.py`).

Fast, low-memory read-only diagnostic gate for verifying IBKR XML 
parent-child option leg identifiers and DuckDB spread classifications.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# Complete 28-label parser catalogue
ALLOWED_STRATEGIES = frozenset({
    "Single Long Call", "Single Short Call", "Single Long Put", "Single Short Put",
    "Bull Call Spread", "Bear Call Spread", "Bull Put Spread", "Bear Put Spread",
    "Ratio Call Spread", "Ratio Put Spread", "Long Straddle", "Short Straddle",
    "Long Strangle", "Short Strangle", "Synthetic Long Stock", "Synthetic Short Stock",
    "Risk Reversal", "Call Butterfly", "Put Butterfly", "Call Broken Wing Butterfly",
    "Put Broken Wing Butterfly", "Iron Butterfly", "Iron Condor",
    "Call Calendar Spread", "Put Calendar Spread", "Call Diagonal Spread", "Put Diagonal Spread",
    "Custom/Review",
})

OPTION_FIELDS = (
    "orderID", "ibOrderID", "brokerageOrderID", "orderReference",
    "ibExecID", "dateTime", "underlyingSymbol", "symbol",
    "putCall", "strike", "expiry", "quantity", "buySell",
)

GROUPING_CANDIDATES = ("brokerageOrderID", "orderReference", "orderID", "ibOrderID")
EXPECTED_TABLES = ("broker_executions", "spread_executions")


def heading(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def inspect_xml(xml_path: Path, sample_size: int) -> bool:
    heading("STEP 1 — IBKR FLEX XML INSPECTOR")
    print(f"XML: {xml_path}")

    sample_trades: list[dict[str, str]] = []
    total_trades = 0
    candidate_counts: dict[str, Counter[str]] = {field: Counter() for field in GROUPING_CANDIDATES}
    candidate_populated: dict[str, int] = {field: 0 for field in GROUPING_CANDIDATES}

    try:
        context = ET.iterparse(xml_path, events=("end",))
        for _, elem in context:
            tag_name = elem.tag.rsplit("}", 1)[-1]
            if tag_name == "Trade" and elem.get("assetCategory") == "OPT":
                total_trades += 1
                attribs = dict(elem.attrib)

                # Store bounded sample only
                if len(sample_trades) < sample_size:
                    sample_trades.append(attribs)

                # Process identifier counters in a single streaming pass
                for field in GROUPING_CANDIDATES:
                    val = attribs.get(field)
                    if val not in (None, ""):
                        candidate_populated[field] += 1
                        candidate_counts[field][val] += 1

                elem.clear()  # Free XML memory instantly
    except (ET.ParseError, OSError) as exc:
        print(f"FAIL: Cannot read XML file {xml_path}: {exc}")
        return False

    print(f"Option Trade elements found: {total_trades}")
    if total_trades == 0:
        print('FAIL: No <Trade assetCategory="OPT"> elements were found.')
        return False

    # Print sample leg details
    for index, trade in enumerate(sample_trades, start=1):
        print(f"\n--- Option leg {index} ---")
        for field in OPTION_FIELDS:
            print(f"  {field:20} {trade.get(field) or '<missing>'}")

    print("\nGrouping identifier coverage across all option legs:")
    safe_candidates: list[str] = []

    for field in GROUPING_CANDIDATES:
        pop_count = candidate_populated[field]
        distinct_count = len(candidate_counts[field])
        repeated = sum(count for count in candidate_counts[field].values() if count > 1)

        print(
            f"  {field:20} populated={pop_count:>4}/{total_trades:<4} "
            f"distinct={distinct_count:>4} repeated-leg-rows={repeated:>4}"
        )
        if field != "ibOrderID" and repeated:
            safe_candidates.append(field)

    if safe_candidates:
        print(f"PASS: Parent package-level grouping candidates found: {', '.join(safe_candidates)}")
    else:
        print("REVIEW: No non-ibOrderID candidate repeats across option legs. Verify spread groupings.")

    ib_order_ids_count = candidate_populated["ibOrderID"]
    if ib_order_ids_count > 0 and len(candidate_counts["ibOrderID"]) == ib_order_ids_count:
        print("NOTE: ibOrderID is 100% unique per leg; DO NOT use it as a multi-leg grouping key.")

    return True


def inspect_database(db_path: Path) -> bool:
    heading("STEP 2 — DUCKDB READ-ONLY VERIFICATION")
    print(f"Database: {db_path}")
    if not db_path.is_file():
        print("FAIL: Database file does not exist.")
        return False

    try:
        import duckdb
    except ImportError:
        print("FAIL: duckdb is not installed in active environment.")
        return False

    try:
        connection = duckdb.connect(str(db_path), read_only=True)
    except Exception as exc:
        print(f"FAIL: Could not open DuckDB read-only: {exc}")
        return False

    success = True
    try:
        tables_res = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        tables = {str(row[0]) for row in tables_res}
        print("Tables: " + (", ".join(sorted(tables)) or "<none>"))

        for table_name in EXPECTED_TABLES:
            if table_name not in tables:
                print(f"FAIL: Required table missing: {table_name}")
                success = False
                continue
            cols = [str(r[1]) for r in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()]
            print(f"\n{table_name} columns ({len(cols)}): {', '.join(cols)}")

        if "spread_executions" not in tables:
            return False

        print("\nStrategy breakdown:")
        breakdown = connection.execute(
            """
            SELECT strategy_type, COUNT(*) AS spread_rows
            FROM spread_executions
            GROUP BY strategy_type
            ORDER BY spread_rows DESC, strategy_type
            """
        ).fetchall()

        for strategy, count in breakdown:
            label = "<NULL>" if strategy is None else str(strategy)
            print(f"  {label:30} {count}")

        # Check for unapproved strategies against full vocabulary
        unsupported = [row for row in breakdown if row[0] not in ALLOWED_STRATEGIES or row[0] is None]
        if unsupported:
            success = False
            print("\nFAIL: Persisted strategies outside vocabulary or NULL found:")
            for strategy, count in unsupported:
                label = "<NULL>" if strategy is None else str(strategy)
                print(f"  {label:30} {count}")
        else:
            print("\nPASS: All persisted classifications adhere to the strategy vocabulary.")

        # Regex check for remaining single-leg option persistences
        single_leg_labels = connection.execute(
            """
            SELECT strategy_type, COUNT(*) AS spread_rows
            FROM spread_executions
            WHERE regexp_matches(
                coalesce(strategy_type, ''),
                '(?i)(single|long\\s+(call|put)|short\\s+(call|put))'
            )
            GROUP BY strategy_type
            ORDER BY strategy_type
            """
        ).fetchall()

        if single_leg_labels:
            success = False
            print("\nFAIL: False single-leg classifications remain:")
            for strategy, count in single_leg_labels:
                print(f"  {strategy:30} {count}")
        else:
            print("PASS: No false single-leg option classifications detected.")

    except Exception as exc:
        print(f"FAIL: Database verification error: {exc}")
        success = False
    finally:
        connection.close()

    return success


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ProfitMax Ingestion Verification Suite (verify_ingestion.py)"
    )
    parser.add_argument("--xml", type=Path, required=True, help="IBKR Flex XML export file path")
    parser.add_argument("--db", type=Path, required=True, help="ProfitMax DuckDB file path")
    parser.add_argument("--sample-size", type=int, default=8, help="Sample size for XML leg display")
    args = parser.parse_args()

    if args.sample_size < 1:
        print("FAIL: --sample-size must be at least 1.")
        return 2

    xml_ok = inspect_xml(args.xml, args.sample_size)
    db_ok = inspect_database(args.db)

    heading("INGESTION VERIFICATION RESULT")
    if xml_ok and db_ok:
        print("PASS: Ingestion verification diagnostics completed successfully.")
        return 0
    print("FAIL: Resolve flagged issues prior to code deployment.")
    return 1


if __name__ == "__main__":
    sys.exit(main())