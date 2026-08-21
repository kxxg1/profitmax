from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ibis
import pandas as pd
from app.core.db import DB_PATH

router = APIRouter(prefix="/api/v1/trades", tags=["Trades"])

# Connect to persistent DuckDB database via Ibis
con = ibis.duckdb.connect(str(DB_PATH))

class TradeOverrideRequest(BaseModel):
    spread_id: str
    new_strategy_type: str

@router.get("/")
def get_all_spread_trades():
    """
    Returns all reconstructed spread executions sorted by created_at descending.
    Converts NaN/NA float values to Python None (JSON null) to prevent 500 serialization crashes.
    """
    try:
        t = con.table("spread_executions")
        
        # 1. Execute Ibis query to pull Pandas DataFrame
        df = t.order_by(ibis.desc("created_at")).execute()
        
        # 2. Cast columns to object type to prevent float columns from forcing None back to NaN
        df = df.astype(object).where(pd.notna(df), None)
        
        # 3. Return clean JSON-compliant list of dictionaries
        return df.to_dict(orient="records")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))