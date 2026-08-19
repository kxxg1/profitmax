import polars as pl
import xml.etree.ElementTree as ET
from pathlib import Path
import pandera.polars as pa
from datetime import datetime
import zoneinfo
from app.core.db import get_db_connection


# 1. Strict Pandera Schema
class TradeSchema(pa.DataFrameModel):
    tradeID: str = pa.Field(coerce=True)
    combo_id: str = pa.Field(coerce=True)
    dateTime: str = pa.Field(coerce=True)
    symbol: str = pa.Field(coerce=True)
    underlying: str = pa.Field(coerce=True)
    expiration: str = pa.Field(coerce=True)
    right: str = pa.Field(coerce=True, isin=["C", "P"])
    strike: float = pa.Field(coerce=True)
    quantity: float = pa.Field(coerce=True)
    tradePrice: float = pa.Field(coerce=True)
    proceeds: float = pa.Field(coerce=True)
    net_cash_flow: str = pa.Field(coerce=True, isin=["Credit", "Debit", "Even"])
    strategy_type: str = pa.Field(coerce=True)
    unique_strikes: int = pa.Field(coerce=True, ge=1)
    contract_legs: int = pa.Field(coerce=True, ge=1)
    spread_units: float = pa.Field(coerce=True, ge=0)
    dte: int = pa.Field(coerce=True, ge=0)
    is_user_overridden: bool = pa.Field(coerce=True)


def calculate_ny_dte(expiry_str: str) -> int:
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
    """
    Level 2 Structural Fingerprinting: Evaluates exact strike geometry and quantity symmetry.
    """
    total_contract_legs = len(group_df)
    expirations = group_df["expiration"].n_unique()
    unique_strikes_count = group_df["strike"].n_unique()
    
    # Sort legs by strike price for geometric comparison
    sorted_df = group_df.sort("strike")
    strikes = sorted_df["strike"].to_list()
    qtys = sorted_df["merged_quantity"].to_list()
    rights = sorted_df["right"].to_list()

    calls = group_df.filter(pl.col("right") == "C").sort("strike")
    puts = group_df.filter(pl.col("right") == "P").sort("strike")
    
    min_qty = group_df["merged_quantity"].abs().min()
    spread_units = float(min_qty) if min_qty is not None else 1.0
    cash_flow_label = "Credit" if raw_proceeds_sum > 0 else ("Debit" if raw_proceeds_sum < 0 else "Even")
    
    base_metrics = {
        "net_cash_flow": cash_flow_label, 
        "unique_strikes": unique_strikes_count, 
        "contract_legs": total_contract_legs, 
        "spread_units": spread_units
    }

    # ==========================================
    # 1. VERTICAL SPREADS (2 Legs, 1 Expiry)
    # ==========================================
    if total_contract_legs == 2 and expirations == 1 and unique_strikes_count == 2:
        if len(calls) == 2:
            k_long = calls.filter(pl.col("merged_quantity") > 0)["strike"][0]
            k_short = calls.filter(pl.col("merged_quantity") < 0)["strike"][0]
            strategy = "Bear Call Spread" if k_short < k_long else "Bull Call Spread"
            return {**base_metrics, "strategy_type": strategy}
            
        if len(puts) == 2:
            k_long = puts.filter(pl.col("merged_quantity") > 0)["strike"][0]
            k_short = puts.filter(pl.col("merged_quantity") < 0)["strike"][0]
            strategy = "Bull Put Spread" if k_short > k_long else "Bear Put Spread"
            return {**base_metrics, "strategy_type": strategy}

    # ==========================================
    # 2. BUTTERFLIES & BWBs (3 Legs, 1 Expiry)
    # ==========================================
    if total_contract_legs == 3 and expirations == 1 and unique_strikes_count == 3:
        # Check normalized quantities (e.g., +1, -2, +1 or -1, +2, -1)
        q1, q2, q3 = qtys
        is_standard_fly = (q1 > 0 and q2 < 0 and q3 > 0 and abs(q2) == abs(q1) + abs(q3))
        is_inverse_fly  = (q1 < 0 and q2 > 0 and q3 < 0 and abs(q2) == abs(q1) + abs(q3))

        if (is_standard_fly or is_inverse_fly):
            wing1 = round(abs(strikes[1] - strikes[0]), 2)
            wing2 = round(abs(strikes[2] - strikes[1]), 2)
            
            if len(calls) == 3:
                strategy = "Call Butterfly" if wing1 == wing2 else "Call BWB"
                return {**base_metrics, "strategy_type": strategy}
            elif len(puts) == 3:
                strategy = "Put Butterfly" if wing1 == wing2 else "Put BWB"
                return {**base_metrics, "strategy_type": strategy}

    # ==========================================
    # 3. IRON BUTTERFLIES (4 Legs, 3 Strikes)
    # ==========================================
    if total_contract_legs == 4 and expirations == 1 and unique_strikes_count == 3:
        long_calls = calls.filter(pl.col("merged_quantity") > 0)
        short_calls = calls.filter(pl.col("merged_quantity") < 0)
        long_puts = puts.filter(pl.col("merged_quantity") > 0)
        short_puts = puts.filter(pl.col("merged_quantity") < 0)

        if len(long_calls) == 1 and len(short_calls) == 1 and len(long_puts) == 1 and len(short_puts) == 1:
            lp_k = long_puts["strike"][0]
            sp_k = short_puts["strike"][0]
            sc_k = short_calls["strike"][0]
            lc_k = long_calls["strike"][0]

            # Strict Iron Butterfly Geometry: K1 < K2 < K3 and Short Call == Short Put
            if lp_k < sp_k and sp_k == sc_k and sc_k < lc_k:
                return {**base_metrics, "strategy_type": "Iron Butterfly"}

    # ==========================================
    # 4. IRON CONDORS (4 Legs, 4 Strikes)
    # ==========================================
    if total_contract_legs == 4 and expirations == 1 and unique_strikes_count == 4:
        long_calls = calls.filter(pl.col("merged_quantity") > 0)
        short_calls = calls.filter(pl.col("merged_quantity") < 0)
        long_puts = puts.filter(pl.col("merged_quantity") > 0)
        short_puts = puts.filter(pl.col("merged_quantity") < 0)

        if len(long_calls) == 1 and len(short_calls) == 1 and len(long_puts) == 1 and len(short_puts) == 1:
            lp_k = long_puts["strike"][0]
            sp_k = short_puts["strike"][0]
            sc_k = short_calls["strike"][0]
            lc_k = long_calls["strike"][0]

            # Strict Iron Condor Geometry: K1 < K2 < K3 < K4
            if lp_k < sp_k < sc_k < lc_k:
                return {**base_metrics, "strategy_type": "Iron Condor"}

    # ==========================================
    # 5. CALENDARS & DIAGONALS (2 Legs, 2 Expiries)
    # ==========================================
    if total_contract_legs == 2 and expirations == 2:
        if len(puts) == 2:
            strategy = "Put Calendar Spread" if unique_strikes_count == 1 else "Put Diagonal Spread"
            return {**base_metrics, "strategy_type": strategy}
        if len(calls) == 2:
            strategy = "Call Calendar Spread" if unique_strikes_count == 1 else "Call Diagonal Spread"
            return {**base_metrics, "strategy_type": strategy}

    # ==========================================
    # LEVEL 3: NO MATCH -> CUSTOM
    # ==========================================
    return {**base_metrics, "strategy_type": "Custom / Unknown"}


def process_ibkr_flex_file(file_path: Path):
    print(f"[Ingestion] Processing file: {file_path}")
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        trades_data = []
        for elem in root.iter('Trade'):
            if elem.get('assetCategory') == 'OPT':
                raw_qty = float(elem.get('quantity', 0))
                buy_sell = elem.get('buySell', '').upper()
                proceeds = float(elem.get('proceeds', 0))
                
                # Normalize quantity direction
                if buy_sell in ['SELL', 'SL', 'S'] or (buy_sell == '' and proceeds > 0):
                    signed_qty = -abs(raw_qty)
                else:
                    signed_qty = abs(raw_qty)

                trades_data.append({
                    'tradeID': elem.get('tradeID'),
                    'dateTime': elem.get('dateTime'),
                    'symbol': elem.get('symbol'),
                    'underlying': elem.get('underlyingSymbol'),
                    'expiration': elem.get('expiry'),
                    'strike': elem.get('strike'),
                    'right': elem.get('putCall'),
                    'quantity': signed_qty,
                    'tradePrice': elem.get('tradePrice'),
                    'proceeds': proceeds
                })

        if not trades_data:
            return {"status": "error", "message": "No valid option trades found in XML."}

        # Convert to Polars
        df = pl.DataFrame(trades_data).with_columns([
            pl.col("quantity").cast(pl.Float64),
            pl.col("tradePrice").cast(pl.Float64),
            pl.col("proceeds").cast(pl.Float64),
            pl.col("strike").cast(pl.Float64)
        ])

        # Generate deterministic package ID
        df = df.with_columns((pl.col("dateTime") + "_" + pl.col("underlying")).alias("combo_id"))

        # Calculate accurate NY-anchored DTE
        dte_list = [calculate_ny_dte(exp) for exp in df["expiration"]]
        df = df.with_columns(pl.Series("dte", dte_list))

        # Consolidate partial fills
        merged_contracts = df.group_by(
            ["combo_id", "dateTime", "symbol", "underlying", "expiration", "strike", "right"]
        ).agg([
            pl.col("quantity").sum().alias("merged_quantity"),
            pl.col("proceeds").sum().alias("merged_proceeds")
        ])

        # Execute Level 2 Fingerprinting
        combo_ids = df["combo_id"].unique().to_list()
        strategy_mappings = []

        for c_id in combo_ids:
            sub_merged = merged_contracts.filter(pl.col("combo_id") == c_id)
            raw_proceeds_sum = sub_merged["merged_proceeds"].sum()
            
            classification = classify_merged_combo(sub_merged, raw_proceeds_sum)
            strategy_mappings.append({
                "combo_id": c_id,
                **classification
            })

        strat_mapping_df = pl.DataFrame(strategy_mappings)

        # Join strategy metrics back to raw execution rows
        final_df = df.join(strat_mapping_df, on="combo_id", how="left").with_columns(pl.lit(False).alias("is_user_overridden"))

        # Pandera Validation & Native DuckDB Overwrite
        final_df = TradeSchema.validate(final_df)
        conn = get_db_connection()
        try:
            conn.execute("DROP TABLE IF EXISTS broker_events") 
            conn.execute("CREATE TABLE broker_events AS SELECT * FROM final_df")
            print("[Ingestion] ✅ Successfully parsed XML, executed strict geometric fingerprinting, and stored in DuckDB.")
            return {"status": "success", "rows": len(final_df)}
        finally:
            conn.close()

    except Exception as e:
        print(f"[Ingestion] ❌ Error processing file: {e}")
        return {"status": "error", "message": str(e)}