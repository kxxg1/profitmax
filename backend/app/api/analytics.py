from fastapi import APIRouter, HTTPException
import ibis
from app.core.db import DB_PATH

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

# Connect Ibis to DuckDB using the absolute path from your core config
con = ibis.duckdb.connect(str(DB_PATH))

@router.get("/order-types")
def get_order_type_analytics():
    """Aggregates execution performance using type-safe Ibis expressions."""
    try:
        # Bind to the DuckDB table
        t = con.table("spread_executions")
        
        # Build the analytical query programmatically (No raw SQL strings!)
        query = (
            t.group_by(["order_type", "strategy_type", "net_cash_flow"])
            .aggregate(
                total_spreads=t.count(),
                avg_entry_cashflow=t["entry_fill_cashflow"].mean(),
                avg_entry_slippage=t["entry_slippage"].mean(),
                avg_entry_efficiency_pct=t["entry_efficiency_pct"].mean(),
                avg_commission_per_spread=t["total_commissions"].mean()
            )
            .order_by(ibis.desc("total_spreads"))
        )
        
        # Execute the query in DuckDB (returns a DataFrame) and output as JSON-ready dicts
        return query.execute().to_dict(orient="records")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))