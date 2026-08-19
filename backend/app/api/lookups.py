from fastapi import APIRouter
from app.core.db import DB_PATH
import ibis

router = APIRouter(prefix="/api/v1/lookups", tags=["Lookups"])
con = ibis.duckdb.connect(str(DB_PATH))

@router.get("/order-types")
def get_order_types():
    """Returns distinct order types present in DuckDB for AG Grid filters."""
    try:
        t = con.table("spread_executions")
        types = t.select("order_type").distinct().execute()["order_type"].tolist()
        return types if types else ["LMT", "MKT", "STP", "STP LMT", "MIDPX", "PEGMID"]
    except Exception:
        return ["LMT", "MKT", "STP", "STP LMT", "MIDPX", "PEGMID"]

@router.get("/strategy-types")
def get_strategy_types():
    """Returns OIC-compliant option strategy types."""
    return [
        "Bull Call Spread", "Bear Call Spread", "Bull Put Spread", "Bear Put Spread",
        "Call Butterfly", "Put Butterfly", "Call BWB", "Put BWB",
        "Iron Butterfly", "Iron Condor", "Call Calendar Spread", "Put Calendar Spread",
        "Call Diagonal Spread", "Put Diagonal Spread", "Single Long Call", "Single Short Call",
        "Single Long Put", "Single Short Put", "Custom / Unknown"
    ]

@router.get("/execution-sides")
def get_execution_sides():
    return ["ENTRY", "EXIT"]

@router.get("/liquidity-buckets")
def get_liquidity_buckets():
    return ["High Liquidity (<5% Width)", "Moderate Liquidity (5-10% Width)", "Low Liquidity (>10% Width)"]