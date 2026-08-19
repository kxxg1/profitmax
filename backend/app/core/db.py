import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "profitmax.duckdb"

def get_db_connection():
    """
    Initializes DuckDB connection and sets up normalized database tables
    for spread executions, raw contract legs, quote snapshots, and pattern memory.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    
    # 1. Raw Contract Executions (Evidence Layer)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS broker_executions (
            trade_id VARCHAR PRIMARY KEY,
            order_id VARCHAR NOT NULL,
            exec_id VARCHAR,
            brokerage_order_id VARCHAR,
            order_reference VARCHAR,
            combo_id VARCHAR NOT NULL,
            date_time VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            underlying VARCHAR NOT NULL,
            expiration VARCHAR NOT NULL,
            strike DOUBLE NOT NULL,
            "right" VARCHAR NOT NULL,
            quantity DOUBLE NOT NULL,
            trade_price DOUBLE NOT NULL,
            proceeds DOUBLE NOT NULL,
            commission DOUBLE NOT NULL,
            exchange VARCHAR,
            order_type VARCHAR NOT NULL,
            is_api_order BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Reconstructed Spread Executions (Analytics Layer)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS spread_executions (
            spread_id VARCHAR PRIMARY KEY,
            order_id VARCHAR NOT NULL,
            order_reference VARCHAR,
            underlying VARCHAR NOT NULL,
            strategy_type VARCHAR NOT NULL,
            net_cash_flow VARCHAR NOT NULL,
            order_type VARCHAR NOT NULL,
            execution_side VARCHAR DEFAULT 'ENTRY',
            spread_units DOUBLE NOT NULL,
            unique_strikes INTEGER NOT NULL,
            contract_legs INTEGER NOT NULL,
            dte INTEGER NOT NULL,
            
            -- Canonical Pricing Metrics (Positive = Credit/Inflow, Negative = Debit/Outflow)
            entry_fill_cashflow DOUBLE NOT NULL,
            entry_mid_cashflow DOUBLE,
            entry_slippage DOUBLE,
            entry_efficiency_pct DOUBLE,
            
            exit_fill_cashflow DOUBLE,
            exit_mid_cashflow DOUBLE,
            exit_slippage DOUBLE,
            exit_efficiency_pct DOUBLE,
            
            total_commissions DOUBLE NOT NULL,
            total_execution_drag DOUBLE,
            
            -- Excursion Analytics
            mae_mid DOUBLE,
            mae_executable DOUBLE,
            mfe_mid DOUBLE,
            mfe_executable DOUBLE,
            exit_capture_pct DOUBLE,
            
            -- Liquidity & Execution Quality
            spread_width DOUBLE,
            spread_width_pct DOUBLE,
            size_coverage_pct DOUBLE,
            partial_fill_count INTEGER DEFAULT 0,
            reprice_count INTEGER DEFAULT 0,
            
            is_user_overridden BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Spread Quote Snapshots (MAE/MFE & Price Path Reconstruction)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS spread_quote_snapshots (
            snapshot_id VARCHAR PRIMARY KEY,
            spread_id VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            spread_bid DOUBLE NOT NULL,
            spread_ask DOUBLE NOT NULL,
            spread_mid DOUBLE NOT NULL,
            spread_bid_size DOUBLE,
            spread_ask_size DOUBLE,
            underlying_bid DOUBLE,
            underlying_ask DOUBLE,
            underlying_mid DOUBLE,
            quote_source VARCHAR NOT NULL,
            quote_staleness_ms INTEGER,
            delta DOUBLE,
            gamma DOUBLE,
            theta DOUBLE,
            vega DOUBLE
        )
    """)

    # 4. Alpha Vantage & Market Data Cache (Minimizes Token / API Usage)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data_cache (
            cache_key VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            data_type VARCHAR NOT NULL,
            payload_json VARCHAR NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)

    # 5. User Pattern Memory (Self-Learning Fingerprints)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_fingerprints (
            fingerprint_hash VARCHAR PRIMARY KEY,
            strategy_type VARCHAR NOT NULL,
            contract_legs INTEGER NOT NULL,
            unique_strikes INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    return conn