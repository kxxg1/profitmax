from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ibis
import pandas as pd
from typing import List, Dict, Any

from app.core.db import DB_PATH
from app.schemas.trades import (
    CompletedTradeRow,
    completed_trade_from_duckdb_row,
    completed_trade_grid_payload,
)

router = APIRouter(prefix="/api/v1/trades", tags=["Trades"])

# Connect to persistent DuckDB database via Ibis
con = ibis.duckdb.connect(str(DB_PATH))

class TradeOverrideRequest(BaseModel):
    spread_id: str
    new_strategy_type: str

@router.get("/", response_model=List[Dict[str, Any]])
def get_all_spread_trades():
    """
    Returns all reconstructed trade packages validated through the Pydantic CompletedTradeRow schema.
    Includes legacy aliases so the current AG Grid frontend works without breaking.
    """
    try:
        t = con.table("spread_executions")
        
        # 1. Execute query to get raw records
        df = t.order_by(ibis.desc("created_at")).execute()
        
        # 2. Convert DataFrame rows into validated CompletedTradeRow models & format payloads
        columns = list(df.columns)
        validated_payloads = []
        
        for _, row in df.iterrows():
            # Validate DuckDB row against the strict schema
            trade_row: CompletedTradeRow = completed_trade_from_duckdb_row(
                columns=columns, 
                row=row.to_dict()
            )
            
            # Emit grid payload with legacy aliases (symbol, compactSpread, strategy, etc.)
            payload = completed_trade_grid_payload(trade_row, include_legacy_aliases=False)
            validated_payloads.append(payload)
            
        return validated_payloads
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))