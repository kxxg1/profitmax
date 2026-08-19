from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ibis
from app.core.db import DB_PATH

router = APIRouter(prefix="/api/v1/trades", tags=["Trades"])
con = ibis.duckdb.connect(str(DB_PATH))

class TradeOverrideRequest(BaseModel):
    spread_id: str
    new_strategy_type: str

@router.get("/")
def get_all_spread_trades():
    """Returns all reconstructed spread executions."""
    try:
        t = con.table("spread_executions")
        # Execute the query and return as list of dictionaries
        return t.order_by(ibis.desc("created_at")).execute().to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))