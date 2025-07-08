
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from crawler.db.supabase_client import supabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_urls() -> List[str]:
    """Fetches all existing page_urls from the raw_scraped_pages table."""
    try:
        response = supabase.table("raw_scraped_pages").select("page_url").execute()
        if response.data:
            return [item['page_url'] for item in response.data]
        return []
    except Exception as e:
        logger.error(f"Error fetching all URLs from raw_scraped_pages: {e}")
        return []

def bulk_insert_raw_urls(pages_data: List[Dict[str, Any]]) -> None:
    """Inserts a list of new URLs into the raw_scraped_pages table."""
    try:
        response = supabase.table("raw_scraped_pages").insert(pages_data).execute()
        logger.info(f"Successfully inserted {len(response.data)} new URLs.")
    except Exception as e:
        logger.error(f"Error bulk inserting new URLs: {e}")

def get_pending_pages_to_parse() -> List[Dict[str, Any]]:
    """Fetches all rows from raw_scraped_pages where status is 'pending'."""
    try:
        response = supabase.table("raw_scraped_pages").select("*").eq("status", "pending").execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching pending pages: {e}")
        return []

def update_page_as_parsed(page_id: str, parsed_data: Dict[str, Any]) -> None:
    """Updates a page's status to 'parsed' and saves the parsed content."""
    update_payload = {
        **parsed_data,
        "status": "parsed",
        "parsed_at": datetime.utcnow().isoformat()
    }
    try:
        supabase.table("raw_scraped_pages").update(update_payload).eq("id", page_id).execute()
        logger.info(f"Successfully updated page {page_id} as parsed.")
    except Exception as e:
        logger.error(f"Error updating page {page_id} as parsed: {e}")

def update_page_with_error(page_id: str, error_type: str, error_message: str) -> None:
    """Logs a parsing failure for a specific page."""
    update_payload = {
        "status": "failed_parsing",
        "error_type": error_type,
        "error_message": error_message
    }
    try:
        supabase.table("raw_scraped_pages").update(update_payload).eq("id", page_id).execute()
        logger.info(f"Successfully logged error for page {page_id}.")
    except Exception as e:
        logger.error(f"Error logging error for page {page_id}: {e}")
