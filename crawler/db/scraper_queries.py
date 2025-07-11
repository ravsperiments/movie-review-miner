import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import random

from crawler.db.supabase_client import supabase

# Configure logging for this module.
# This ensures that messages from this file are properly captured in the overall logging system.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_urls() -> List[str]:
    """
    Fetches all existing `page_url` entries from the `raw_scraped_pages` table.

    This function is primarily used to retrieve a list of URLs that have already
    been scraped and stored in the database. This helps in implementing early
    stopping mechanisms during the scraping process, preventing redundant work
    and ensuring that only new links are processed.

    Returns:
        List[str]: A list of strings, where each string is a `page_url`.
                   Returns an empty list if no URLs are found or an error occurs.
    """
    try:
        # Query the 'raw_scraped_pages' table to select all 'page_url' columns.
        response = supabase.table("raw_scraped_pages").select("page_url").execute()
        
        # If data is returned, extract the 'page_url' from each item.
        if response.data:
            return [item['page_url'] for item in response.data]
        return []
    except Exception as e:
        # Log any errors that occur during the database query.
        logger.error(f"Error fetching all URLs from raw_scraped_pages: {e}")
        return []


def bulk_insert_raw_urls(pages_data: List[Dict[str, Any]]) -> None:
    """
    Inserts a list of raw page data (containing URLs and metadata) into the
    `raw_scraped_pages` table. It uses an upsert mechanism to handle conflicts
    on the `page_url`, ensuring that duplicate URLs are updated rather than
    causing an error.

    Args:
        pages_data (List[Dict[str, Any]]): A list of dictionaries, where each
                                            dictionary represents a raw page entry.
                                            Expected keys include 'page_url', 'base_url',
                                            'critic_id', 'fetched_at', and 'status'.
    """
    try:
        # Perform a bulk upsert operation. If a 'page_url' already exists,
        # the existing record will be updated with the new data.
        response = supabase.table("raw_scraped_pages").upsert(pages_data, on_conflict="page_url").execute()
        logger.info(f"Successfully inserted {len(response.data)} new URLs.")
    except Exception as e:
        # Log any errors that occur during the bulk insert/upsert operation.
        logger.error(f"Error bulk inserting new URLs: {e}")


def get_pending_pages_to_parse() -> List[Dict[str, Any]]:
    """
    Fetches all entries from the `raw_scraped_pages` table that have a status of 'pending'.

    These are typically pages whose URLs have been scraped but their content
    has not yet been parsed and processed.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a pending page.
                              Returns an empty list if no pending pages are found or an error occurs.
    """
    try:
        # Query the 'raw_scraped_pages' table for records where 'status' is 'pending'.
        response = supabase.table("raw_scraped_pages").select("*").eq("status", "pending").execute()
        
        # Return the data if available, otherwise an empty list.
        return response.data if response.data else []
    except Exception as e:
        # Log any errors during the fetch operation.
        logger.error(f"Error fetching pending pages: {e}")
        return []


def update_page_as_parsed(page_id: str, parsed_data: Dict[str, Any]) -> None:
    """
    Updates a specific page's status to 'parsed' and stores its extracted content.

    This function is called after a raw page's content has been successfully
    parsed. It marks the page as processed and saves the structured data
    extracted during parsing.

    Args:
        page_id (str): The unique identifier (ID) of the page to update.
        parsed_data (Dict[str, Any]): A dictionary containing the structured data
                                     extracted from the page (e.g., title, content).
    """
    # Prepare the payload for the update operation.
    # It includes the parsed data, sets the status to 'parsed', and records the parsing timestamp.
    update_payload = {
        "parsed_title": parsed_data.get("parsed_title"),
        "parsed_short_review": parsed_data.get("parsed_short_review"),
        "parsed_full_review": parsed_data.get("parsed_full_review"),
        "parsed_review_date": parsed_data.get("parsed_review_date"),
        "status": "parsed",
        "parsed_at": datetime.utcnow().isoformat()
    }
    try:
        # Perform the update operation on the 'raw_scraped_pages' table,
        # targeting the record by its 'id'.
        supabase.table("raw_scraped_pages").update(update_payload).eq("id", page_id).execute()
        logger.info(f"Successfully updated page {page_id} as parsed.")
    except Exception as e:
        # Log any errors that occur during the update.
        logger.error(f"Error updating page {page_id} as parsed: {e}")


def update_page_with_error(page_id: str, error_type: str, error_message: str) -> None:
    """
    Logs a parsing failure for a specific page by updating its status to 'failed_parsing'.

    This function is invoked when an error occurs during the parsing of a raw page.
    It records the type of error and a descriptive message for debugging and tracking.

    Args:
        page_id (str): The unique identifier (ID) of the page that failed parsing.
        error_type (str): A string indicating the type of error (e.g., "parsing_error", "network_issue").
        error_message (str): A detailed message describing the error.
    """
    # Prepare the payload for updating the page's status to indicate a parsing failure.
    update_payload = {
        "status": "failed_parsing",
        "error_type": error_type,
        "error_message": error_message
    }
    try:
        # Perform the update operation, setting the status and error details.
        supabase.table("raw_scraped_pages").update(update_payload).eq("id", page_id).execute()
        logger.info(f"Successfully logged error for page {page_id}.")
    except Exception as e:
        # Log any errors that occur while trying to log the original error.
        logger.error(f"Error logging error for page {page_id}: {e}")

def get_parsed_pages() -> List[Dict[str, Any]]:
    """
    Fetches all entries from the `raw_scraped_pages` table that have a status of 'parsed'.

    These are typically pages whose content has been successfully parsed and are ready
    for further processing, such as LLM classification.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a parsed page.
                              Returns an empty list if no parsed pages are found or an error occurs.
    """
    try:
        response = supabase.table("raw_scraped_pages").select("*").eq("status", "parsed").limit(5).execute()
        print(response.data)
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching parsed raw scraped pages: {e}")
        return []
    

def get_unpromoted_pages() -> List[Dict[str, Any]]:
    """
    Fetches all entries from the `raw_scraped_pages` table that have a status of 'parsed'.

    These are typically pages whose content has been successfully parsed and are ready
    for further processing, such as LLM classification.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a parsed page.
                              Returns an empty list if no parsed pages are found or an error occurs.
    """
    try:
        # query raw sccapped pages to get unpublished rows, which returns ~1000 rows
        response = supabase.table("raw_scraped_pages") \
            .select("*") \
            .gt("parsed_review_date", "2018-12-31") \
            .execute()
        # get 200 random sample from the reuturned records
        sampled_rows = random.sample(response.data, 200)
        
        return sampled_rows if sampled_rows else []

    except Exception as e:
        logger.error(f"Error fetching parsed raw scraped pages: {e}")
        return []

