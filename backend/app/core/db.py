import duckdb
from pathlib import Path

# Define the path to the data directory at the root of the backend folder
DATA_DIR = Path("data")

# Ensure the data folder actually exists before we try to put a database in it
DATA_DIR.mkdir(exist_ok=True)

# The absolute path to our specific database file
DB_PATH = DATA_DIR / "profitmax.duckdb"

def get_db_connection():
    """
    Returns a DuckDB connection.
    By using this central function, we ensure every part of our app connects 
    to the exact same profitmax.duckdb file.
    """
    return duckdb.connect(str(DB_PATH))