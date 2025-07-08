import logging
from typing import List, Dict, Any

from crawler.db.supabase_client import supabase

logger = logging.getLogger(__name__)

def get_critics() -> List[Dict[str, Any]]:
    """
    Fetches all critic data from the 'critics' table.
    """
    try:
        response = supabase.table("critics").select("id, name, base_url, bio, created_at, updated_at").execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error fetching critics: {e}")
        return []
