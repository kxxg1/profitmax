from fastapi import APIRouter
from pathlib import Path
from app.services.ibkr_parser import process_ibkr_flex_file

# Create an API router to group our ingestion endpoints
router = APIRouter()

@router.post("/ingest-ibkr")
def trigger_ibkr_ingestion():
    """
    This endpoint will be hit by your Render Cron Job daily.
    It kicks off the SQL-free data pipeline to process IBKR data.
    """
    # For this MVP test, we pass a dummy path.
    # Later, this will download the Flex XML from IBKR or accept an uploaded file.
    dummy_path = Path("dummy_flex_report.xml")
    
    # Call the service function we wrote in ibkr_parser.py
    result = process_ibkr_flex_file(dummy_path)
    
    return result