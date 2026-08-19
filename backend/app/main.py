from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import get_db_connection

# 1. Import all routers
from app.api.ingest import router as ingest_router
from app.api.lookups import router as lookups_router
from app.api.trades import router as trades_router
from app.api.market_data import router as market_data_router
from app.api.analytics import router as analytics_router

# Initialize the FastAPI application
app = FastAPI(
    title="Profit Max Backend Engine API",
    version="1.0.0",
    description="Options Trading Journal with Spread Analytics"
)

# Configure CORS to allow the Vite React frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default local port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register all routers
# Note: Retaining the explicit prefix for ingest_router to prevent breaking existing API calls
app.include_router(ingest_router, prefix="/api", tags=["Ingestion"])

# New analytical routers (These already have their prefixes defined internally, e.g., /api/v1/...)
app.include_router(lookups_router)
app.include_router(trades_router)
app.include_router(market_data_router)
app.include_router(analytics_router)

@app.on_event("startup")
def startup_event():
    """
    When the server starts, briefly connect to the database. 
    This triggers DuckDB to create the profitmax.duckdb file if it doesn't exist yet.
    """
    conn = get_db_connection()
    conn.close()
    print("✅ Profit Max Analytical Database Initialized.")

@app.get("/")
def root():
    return {"status": "online", "system": "Profit Max Backend Engine"}

@app.get("/health")
def health_check():
    """
    A simple endpoint to verify the server is alive and responding.
    """
    return {"status": "ok", "message": "Profit Max Backend is running natively!"}