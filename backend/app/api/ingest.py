from fastapi import APIRouter
from pathlib import Path
from app.services.ibkr_parser import process_ibkr_flex_file

router = APIRouter()

@router.post("/ingest-ibkr")
def trigger_ibkr_ingestion():
    """
    Triggers parsing and DuckDB ingestion for the IBKR Flex XML report.
    """
    # 1. Locate the XML file in backend/data/
    data_dir = Path(__file__).parent.parent.parent / "data"
    xml_path = data_dir / "Profitmax_Flex_Query.xml"
    
    # Fallback if saved directly under backend/
    if not xml_path.exists():
        xml_path = Path(__file__).parent.parent.parent / "Profitmax_Flex_Query.xml"

    # 2. Check file existence
    if not xml_path.exists():
        return {
            "status": "error", 
            "message": f"Flex XML file not found. Place Profitmax_Flex_Query.xml in {data_dir}"
        }
        
    # 3. Process XML with Polars, Pandera, and DuckDB
    result = process_ibkr_flex_file(xml_path)
    return result