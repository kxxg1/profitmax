from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import get_db_connection

# 1. IMPORT THE NEW ROUTER
from app.api.ingest import router as ingest_router 

# Initialize the FastAPI application
app = FastAPI(title="Profit Max API", version="1.0.0")

# Configure CORS to allow the Vite React frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default local port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. ATTACH THE ROUTER TO THE APP
app.include_router(ingest_router, prefix="/api", tags=["Ingestion"])

@app.on_event("startup")
def startup_event():
    """
    When the server starts, briefly connect to the database. 
    This triggers DuckDB to create the profitmax.duckdb file if it doesn't exist yet.
    """
    conn = get_db_connection()
    conn.close()
    print("✅ Profit Max Database Initialized.")

@app.get("/health")
def health_check():
    """
    A simple endpoint to verify the server is alive and responding.
    """
    return {"status": "ok", "message": "Profit Max Backend is running natively!"}