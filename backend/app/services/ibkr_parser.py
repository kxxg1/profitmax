import math
import polars as pl
import xml.etree.ElementTree as ET
from pathlib import Path
import pandera.polars as pa
from datetime import datetime
import zoneinfo
import ibis
from app.core.db import DB_PATH

# Supported strategy vocabulary
CUSTOM_REVIEW = "Custom/Review"
SUPPORTED_STRATEGIES = frozenset(
    {
        "Single Long Call",
        "Single Short Call",
        "Single Long Put",
        "Single Short Put",
        "Bull Call Spread",
        "Bear Call Spread",
        "Bull Put Spread",
        "Bear Put Spread",
        "Ratio Call Spread",
        "Ratio Put Spread",
        "Long Straddle",
        "Short Straddle",
        "Long Strangle",
        "Short Strangle",
        "Synthetic Long Stock",
        "Synthetic Short Stock",
        "Risk Reversal",
        "Call Butterfly",
        "Put Butterfly",
        "Call Broken Wing Butterfly",
        "Put Broken Wing Butterfly",
        "Iron Butterfly",
        "Iron Condor",
        "Call Calendar Spread",
        "Put Calendar Spread",
        "Call Diagonal Spread",
        "Put Diagonal Spread",
        CUSTOM_REVIEW,
    }
)


# ==========================================
# 1. PANDERA SCHEMAS
# ==========================================
class SpreadExecutionSchema(pa.DataFrameModel):
    spread_id: str = pa.Field(coerce=True)
    order_id: str = pa.Field(coerce=True)
    order_reference: str = pa.Field(coerce=True)
    underlying: str = pa.Field(coerce=True)
    strategy_type: str = pa.Field(coerce=True, isin=sorted(SUPPORTED_STRATEGIES))
    net_cash_flow: str = pa.Field(coerce=True, isin=["Credit", "Debit", "Even"])
    order_type: str = pa.Field(coerce=True)
    spread_units: float = pa.Field(coerce=True, ge=0)
    unique_strikes: int = pa.Field(coerce=True, ge=1)
    contract_legs: int = pa.Field(coerce=True, ge=1)
    dte: int = pa.Field(coerce=True, ge=0)
    entry_fill_cashflow: float = pa.Field(coerce=True)
    total_commissions: float = pa.Field(coerce=True, ge=0)
    is_user_overridden: bool = pa.Field(coerce=True)


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def calculate_ny_dte(expiry_str: str) -> int:
    """Calculates DTE anchored to US/Eastern market close (4:00 PM ET)."""
    try:
        ny_tz = zoneinfo.ZoneInfo("America/New_York")
        exp_date = datetime.strptime(expiry_str, "%Y%m%d")
        exp_datetime = datetime(exp_date.year, exp_date.month, exp_date.day, 16, 0, 0, tzinfo=ny_tz)
        now_ny = datetime.now(ny_tz)
        delta = (exp_datetime - now_ny).total_seconds()
        return max(0, int(round(delta / 86400.0)))
    except Exception:
        return 0


def classify_merged_combo(group_df: pl.DataFrame, raw_proceeds_sum: float) -> dict:
    """Production Level 2 Structural Fingerprinting with Ratio & Synthetic support."""
    total_contract_legs = len(group_df)
    expirations = group_df["expiration"].n_unique()
    unique_strikes_count = group_df["strike"].n_unique()

    sorted_df = group_df.sort("strike")
    strikes = sorted_df["strike"].to_list()
    quantities = [round(float(str(q)), 4) for q in sorted_df["merged_quantity"].to_list()]

    calls = group_df.filter(pl.col("right") == "C").sort("strike")
    puts = group_df.filter(pl.col("right") == "P").sort("strike")

    min_qty = group_df["merged_quantity"].abs().min()
    spread_units = float(str(min_qty)) if min_qty is not None else 1.0
    cash_flow_label = "Credit" if raw_proceeds_sum > 0 else ("Debit" if raw_proceeds_sum < 0 else "Even")

    base_metrics = {
        "net_cash_flow": cash_flow_label,
        "unique_strikes": unique_strikes_count,
        "contract_legs": total_contract_legs,
        "spread_units": spread_units,
    }

    def result(strategy: str) -> dict:
        persisted_strategy = strategy if strategy in SUPPORTED_STRATEGIES else CUSTOM_REVIEW
        return {**base_metrics, "strategy_type": persisted_strategy}

    # 1. SINGLE-LEG OPTIONS
    if total_contract_legs == 1:
        qty = group_df["merged_quantity"][0]
        right = group_df["right"][0]
        if right == "C":
            strategy = "Single Long Call" if qty > 0 else "Single Short Call"
        elif right == "P":
            strategy = "Single Long Put" if qty > 0 else "Single Short Put"
        else:
            strategy = CUSTOM_REVIEW
        return result(strategy)

    # 2. TWO-LEG STRATEGIES (Same Expiry)
    if total_contract_legs == 2 and expirations == 1:
        if len(calls) == 2:
            q1, q2 = calls["merged_quantity"].to_list()
            if abs(q1) == abs(q2) and (q1 * q2 < 0):
                k_long = calls.filter(pl.col("merged_quantity") > 0)["strike"][0]
                k_short = calls.filter(pl.col("merged_quantity") < 0)["strike"][0]
                strategy = "Bear Call Spread" if k_short < k_long else "Bull Call Spread"
            elif q1 * q2 < 0:
                strategy = "Ratio Call Spread"
            else:
                strategy = CUSTOM_REVIEW
            return result(strategy)

        if len(puts) == 2:
            q1, q2 = puts["merged_quantity"].to_list()
            if abs(q1) == abs(q2) and (q1 * q2 < 0):
                k_long = puts.filter(pl.col("merged_quantity") > 0)["strike"][0]
                k_short = puts.filter(pl.col("merged_quantity") < 0)["strike"][0]
                strategy = "Bull Put Spread" if k_short > k_long else "Bear Put Spread"
            elif q1 * q2 < 0:
                strategy = "Ratio Put Spread"
            else:
                strategy = CUSTOM_REVIEW
            return result(strategy)

        if len(calls) == 1 and len(puts) == 1:
            q_call = calls["merged_quantity"][0]
            q_put = puts["merged_quantity"][0]

            if unique_strikes_count == 1:
                if q_call > 0 and q_put > 0:
                    strategy = "Long Straddle"
                elif q_call < 0 and q_put < 0:
                    strategy = "Short Straddle"
                else:
                    strategy = "Synthetic Long Stock" if q_call > 0 else "Synthetic Short Stock"
                return result(strategy)

            if unique_strikes_count == 2:
                if q_call > 0 and q_put > 0:
                    strategy = "Long Strangle"
                elif q_call < 0 and q_put < 0:
                    strategy = "Short Strangle"
                else:
                    strategy = "Risk Reversal"
                return result(strategy)

    # 3. BUTTERFLIES & BWBs (3 Legs, 1 Expiry)
    if total_contract_legs == 3 and expirations == 1 and unique_strikes_count == 3:
        q1, q2, q3 = quantities
        is_fly_ratio = math.isclose(abs(q2), abs(q1) + abs(q3), rel_tol=1e-3)
        has_opposing_body = (q1 * q2 < 0) and (q3 * q2 < 0)

        if is_fly_ratio and has_opposing_body:
            wing1 = round(abs(strikes[1] - strikes[0]), 2)
            wing2 = round(abs(strikes[2] - strikes[1]), 2)

            if len(calls) == 3:
                strategy = "Call Butterfly" if math.isclose(wing1, wing2, abs_tol=1e-2) else "Call Broken Wing Butterfly"
                return result(strategy)
            elif len(puts) == 3:
                strategy = "Put Butterfly" if math.isclose(wing1, wing2, abs_tol=1e-2) else "Put Broken Wing Butterfly"
                return result(strategy)

    # 4. IRON BUTTERFLIES (4 Legs, 1 Expiry, 3 Strikes)
    if total_contract_legs == 4 and expirations == 1 and unique_strikes_count == 3:
        long_calls = calls.filter(pl.col("merged_quantity") > 0)
        short_calls = calls.filter(pl.col("merged_quantity") < 0)
        long_puts = puts.filter(pl.col("merged_quantity") > 0)
        short_puts = puts.filter(pl.col("merged_quantity") < 0)

        if len(long_calls) == 1 and len(short_calls) == 1 and len(long_puts) == 1 and len(short_puts) == 1:
            if long_puts["strike"][0] < short_puts["strike"][0] == short_calls["strike"][0] < long_calls["strike"][0]:
                return result("Iron Butterfly")

    # 5. IRON CONDORS (4 Legs, 1 Expiry, 4 Strikes)
    if total_contract_legs == 4 and expirations == 1 and unique_strikes_count == 4:
        long_calls = calls.filter(pl.col("merged_quantity") > 0)
        short_calls = calls.filter(pl.col("merged_quantity") < 0)
        long_puts = puts.filter(pl.col("merged_quantity") > 0)
        short_puts = puts.filter(pl.col("merged_quantity") < 0)

        if len(long_calls) == 1 and len(short_calls) == 1 and len(long_puts) == 1 and len(short_puts) == 1:
            if long_puts["strike"][0] < short_puts["strike"][0] < short_calls["strike"][0] < long_calls["strike"][0]:
                return result("Iron Condor")

    # 6. CALENDARS & DIAGONALS (2 Legs, 2 Expiries)
    if total_contract_legs == 2 and expirations == 2:
        if len(puts) == 2:
            q1, q2 = puts["merged_quantity"].to_list()
            if q1 * q2 < 0:
                strategy = "Put Calendar Spread" if unique_strikes_count == 1 else "Put Diagonal Spread"
                return result(strategy)
        if len(calls) == 2:
            q1, q2 = calls["merged_quantity"].to_list()
            if q1 * q2 < 0:
                strategy = "Call Calendar Spread" if unique_strikes_count == 1 else "Call Diagonal Spread"
                return result(strategy)

    return result(CUSTOM_REVIEW)


# ==========================================
# 3. IBIS SAFE INSERTION
# ==========================================
def insert_safely(broker_df: pl.DataFrame, spread_df: pl.DataFrame, db_path: str):
    """Safely inserts Arrow data structures using Ibis, matching columns by name to preserve DuckDB schema ordering."""
    con = ibis.duckdb.connect(db_path)

    try:
        con.raw_sql("BEGIN TRANSACTION")
        con.raw_sql("DELETE FROM broker_executions")
        con.raw_sql("DELETE FROM spread_executions")

        # Fetch destination schemas directly from DuckDB to align column order by name
        broker_table = con.table("broker_executions")
        spread_table = con.table("spread_executions")

        broker_cols = [col for col in broker_table.columns if col in broker_df.columns]
        spread_cols = [col for col in spread_table.columns if col in spread_df.columns]

        broker_aligned = broker_df.select(broker_cols)
        spread_aligned = spread_df.select(spread_cols)

        con.insert("broker_executions", broker_aligned.to_arrow())
        con.insert("spread_executions", spread_aligned.to_arrow())

        con.raw_sql("COMMIT")
        print("[Ingestion] ✅ Successfully inserted data using type-safe Ibis Arrow bindings.")

    except Exception as e:
        con.raw_sql("ROLLBACK")
        print(f"[Ingestion] ❌ Database error during safe insert: {e}")
        raise e


# ==========================================
# 4. MAIN INGESTION PIPELINE
# ==========================================
def process_ibkr_flex_file(file_path: Path):
    print(f"[Ingestion] Processing file: {file_path}")

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        trades_data = []
        for elem in root.iter("Trade"):
            if elem.get("assetCategory") == "OPT":
                raw_qty = float(elem.get("quantity", 0))
                buy_sell = elem.get("buySell", "").upper()
                proceeds = float(elem.get("proceeds", 0))

                if buy_sell in ["SELL", "SL", "S"] or (buy_sell == "" and proceeds > 0):
                    signed_qty = -abs(raw_qty)
                else:
                    signed_qty = abs(raw_qty)

                # DO NOT use ibOrderID for grouping, as IB assigns unique IDs to each leg.
                order_id = elem.get("orderID") or ""
                brokerage_order_id = elem.get("brokerageOrderID") or ""
                order_ref = elem.get("orderReference") or ""
                exec_id = elem.get("execID") or elem.get("ibExecID") or elem.get("transactionID") or ""
                date_time = elem.get("dateTime") or ""
                underlying = elem.get("underlyingSymbol") or ""

                # CRITICAL FIX: Prioritize parent package ticket over leg-level IDs
                primary_group_key = brokerage_order_id or order_ref or order_id or f"{date_time}_{underlying}"

                trades_data.append(
                    {
                        "trade_id": elem.get("tradeID") or f"TR_{date_time}_{elem.get('strike')}",
                        "order_id": brokerage_order_id or order_id or primary_group_key,
                        "exec_id": exec_id,
                        "brokerage_order_id": brokerage_order_id,
                        "order_reference": order_ref,
                        "combo_id": primary_group_key,
                        "date_time": date_time,
                        "symbol": elem.get("symbol", ""),
                        "underlying": underlying,
                        "expiration": elem.get("expiry", ""),
                        "strike": float(elem.get("strike", 0)),
                        "right": elem.get("putCall", ""),
                        "buy_sell": buy_sell,
                        "quantity": signed_qty,
                        "trade_price": float(elem.get("tradePrice", 0)),
                        "proceeds": proceeds,
                        "commission": abs(float(elem.get("ibCommission", 0) or elem.get("commission", 0))),
                        "exchange": elem.get("exchange", ""),
                        "order_type": elem.get("orderType", "LMT").upper(),
                        "notes": "",
                    }
                )

        if not trades_data:
            return {"status": "error", "message": "No valid option trades found in XML."}

        broker_df = pl.DataFrame(trades_data)

        # Merge partial execution fills per contract
        merged_contracts = broker_df.group_by(
            ["combo_id", "symbol", "underlying", "expiration", "strike", "right"]
        ).agg(
            [
                pl.col("quantity").sum().alias("merged_quantity"),
                pl.col("proceeds").sum().alias("merged_proceeds"),
                pl.col("commission").sum().alias("merged_commission"),
            ]
        )

        combo_ids = broker_df["combo_id"].unique().to_list()
        spread_rows = []

        for c_id in combo_ids:
            sub_raw = broker_df.filter(pl.col("combo_id") == c_id)
            sub_merged = merged_contracts.filter(pl.col("combo_id") == c_id)

            raw_proceeds_sum = float(sub_merged["merged_proceeds"].sum())
            total_commissions = float(sub_merged["merged_commission"].sum())

            classification = classify_merged_combo(sub_merged, raw_proceeds_sum)

            units = classification["spread_units"]
            entry_cashflow = raw_proceeds_sum / units if units > 0 else raw_proceeds_sum

            spread_rows.append(
                {
                    "spread_id": f"SPD_{c_id}",
                    "order_id": sub_raw["order_id"][0],
                    "order_reference": sub_raw["order_reference"][0],
                    "underlying": sub_raw["underlying"][0],
                    "strategy_type": classification["strategy_type"],
                    "net_cash_flow": classification["net_cash_flow"],
                    "order_type": sub_raw["order_type"][0],
                    "spread_units": units,
                    "unique_strikes": classification["unique_strikes"],
                    "contract_legs": classification["contract_legs"],
                    "dte": calculate_ny_dte(sub_raw["expiration"][0]),
                    "entry_fill_cashflow": entry_cashflow,
                    "total_commissions": total_commissions,
                    "is_user_overridden": False,
                }
            )

        spread_df = pl.DataFrame(spread_rows)
        spread_df = SpreadExecutionSchema.validate(spread_df)

        insert_safely(broker_df, spread_df, str(DB_PATH))

        return {"status": "success", "raw_legs": len(broker_df), "spread_executions": len(spread_df)}

    except Exception as e:
        print(f"[Ingestion] ❌ Error processing file: {e}")
        return {"status": "error", "message": str(e)}