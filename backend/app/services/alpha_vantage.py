import os
import json
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from app.core.db import get_db_connection

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "DEMO_KEY")
BASE_URL = "https://www.alphavantage.co/query"

def get_cached_market_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves valid cached payload from DuckDB if available and unexpired."""
    conn = get_db_connection()
    try:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        res = conn.execute(
            """
            SELECT payload_json FROM market_data_cache 
            WHERE cache_key = ? AND expires_at > ?
            """,
            [cache_key, now_utc]
        ).fetchone()
        
        if res:
            print(f"[AlphaVantage Cache] 🎯 Cache HIT for key: {cache_key}")
            return json.loads(res[0])
        return None
    finally:
        conn.close()

def set_cached_market_data(cache_key: str, symbol: str, data_type: str, payload: Dict[str, Any], ttl_hours: int = 24):
    """Persists API payload into DuckDB cache to prevent redundant API calls."""
    conn = get_db_connection()
    try:
        now_dt = datetime.now(timezone.utc)
        expires_dt = now_dt + timedelta(hours=ttl_hours)
        
        conn.execute(
            """
            INSERT INTO market_data_cache (cache_key, symbol, data_type, payload_json, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (cache_key) DO UPDATE SET
                payload_json = EXCLUDED.payload_json,
                fetched_at = EXCLUDED.fetched_at,
                expires_at = EXCLUDED.expires_at
            """,
            [
                cache_key,
                symbol,
                data_type,
                json.dumps(payload),
                now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                expires_dt.strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
        print(f"[AlphaVantage Cache] 💾 Cached data for key: {cache_key} (TTL: {ttl_hours}h)")
    finally:
        conn.close()

async def fetch_option_chain_cached(symbol: str) -> Dict[str, Any]:
    """
    Fetches option chain & Greeks from Alpha Vantage with DuckDB caching.
    Ensures zero token waste on community plan.
    """
    cache_key = f"OPT_CHAIN_{symbol.upper()}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    
    # 1. Check DuckDB Cache
    cached_data = get_cached_market_data(cache_key)
    if cached_data:
        return cached_data

    # 2. Fetch from Alpha Vantage API
    print(f"[AlphaVantage API] 🌐 Fetching live option chain for: {symbol}")
    params = {
        "function": "HISTORICAL_OPTIONS",
        "symbol": symbol.upper(),
        "apikey": ALPHA_VANTAGE_API_KEY
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(BASE_URL, params=params)
        if response.status_code != 200:
            raise Exception(f"Alpha Vantage HTTP Error: {response.status_code}")
        
        data = response.json()
        
        # Handle API Rate Limits
        if "Note" in data or "Information" in data:
            print(f"[AlphaVantage Warning] Rate limit reached: {data}")
            return {"status": "rate_limited", "message": data.get("Note") or data.get("Information")}
        
        # 3. Store in Cache (24-hour TTL for historical end-of-day options data)
        set_cached_market_data(cache_key, symbol, "HISTORICAL_OPTIONS", data, ttl_hours=24)
        return data