import logging
from datetime import datetime
from typing import List, Dict, Any
# import random

try:
    from crawler.db.sqlite_client import get_db
    USE_SQLITE = True
except Exception:
    from crawler.db.supabase_client import supabase
    USE_SQLITE = False

# Configure logging for this module.
# This ensures that messages from this file are properly captured in the overall logging system.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_urls() -> List[str]:
    """
    Fetches all existing `page_url` entries from the `pages` table.

    This function is primarily used to retrieve a list of URLs that have already
    been scraped and stored in the database. This helps in implementing early
    stopping mechanisms during the scraping process, preventing redundant work
    and ensuring that only new links are processed.

    Returns:
        List[str]: A list of strings, where each string is a `page_url`.
                   Returns an empty list if no URLs are found or an error occurs.
    """
    try:
        if USE_SQLITE:
            results = get_db().select("pages", "page_url")
            return [item['page_url'] for item in results] if results else []
        else:
            # Query the 'pages' table to select all 'page_url' columns.
            response = supabase.table("pages").select("page_url").execute()
            # If data is returned, extract the 'page_url' from each item.
            if response.data:
                return [item['page_url'] for item in response.data]
            return []
    except Exception as e:
        # Log any errors that occur during the database query.
        logger.error(f"Error fetching all URLs from pages: {e}")
        return []


def bulk_insert_raw_urls(pages_data: List[Dict[str, Any]]) -> None:
    """
    Inserts a list of raw page data (containing URLs and metadata) into the
    `pages` table. It uses an upsert mechanism to handle conflicts
    on the `page_url`, ensuring that duplicate URLs are updated rather than
    causing an error.

    Args:
        pages_data (List[Dict[str, Any]]): A list of dictionaries, where each
                                            dictionary represents a page entry.
                                            Expected keys include 'page_url', 'base_url',
                                            'critic_id', 'fetched_at', and 'status'.
    """
    try:
        if USE_SQLITE:
            get_db().upsert("pages", pages_data, conflict_column="page_url")
            logger.info(f"Successfully inserted {len(pages_data)} new URLs.")
        else:
            # Perform a bulk upsert operation. If a 'page_url' already exists,
            # the existing record will be updated with the new data.
            response = supabase.table("pages").upsert(pages_data, on_conflict="page_url").execute()
            logger.info(f"Successfully inserted {len(response.data)} new URLs.")
    except Exception as e:
        # Log any errors that occur during the bulk insert/upsert operation.
        logger.error(f"Error bulk inserting new URLs: {e}")


def get_pending_pages_to_parse() -> List[Dict[str, Any]]:
    """
    Fetches all entries from the `pages` table that have a status of 'pending'.

    These are typically pages whose URLs have been scraped but their content
    has not yet been parsed and processed.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a pending page.
                              Returns an empty list if no pending pages are found or an error occurs.
    """
    try:
        if USE_SQLITE:
            return get_db().select("pages", where="status = ?", params=("pending",))
        else:
            # Query the 'pages' table for records where 'status' is 'pending'.
            response = supabase.table("pages").select("*").eq("status", "pending").execute()
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
        if USE_SQLITE:
            get_db().update("pages", update_payload, "id = ?", (page_id,))
            logger.info(f"Successfully updated page {page_id} as parsed.")
        else:
            # Perform the update operation on the 'pages' table,
            # targeting the record by its 'id'.
            supabase.table("pages").update(update_payload).eq("id", page_id).execute()
            logger.info(f"Successfully updated page {page_id} as parsed.")
    except Exception as e:
        # Log any errors that occur during the update.
        logger.error(f"Error updating page {page_id} as parsed: {e}")


def update_page_with_error(page_id: str, error_type: str, error_message: str) -> None:
    """
    Logs a parsing failure for a specific page by updating its status to 'parsing_failed'.

    This function is invoked when an error occurs during the parsing of a raw page.
    It records the type of error and a descriptive message for debugging and tracking.

    Args:
        page_id (str): The unique identifier (ID) of the page that failed parsing.
        error_type (str): A string indicating the type of error (e.g., "parsing_error", "network_issue").
        error_message (str): A detailed message describing the error.
    """
    # Prepare the payload for updating the page's status to indicate a parsing failure.
    update_payload = {
        "status": "parsing_failed",
        "error_type": error_type,
        "error_message": error_message
    }
    try:
        if USE_SQLITE:
            get_db().update("pages", update_payload, "id = ?", (page_id,))
            logger.info(f"Successfully logged error for page {page_id}.")
        else:
            # Perform the update operation, setting the status and error details.
            supabase.table("pages").update(update_payload).eq("id", page_id).execute()
            logger.info(f"Successfully logged error for page {page_id}.")
    except Exception as e:
        # Log any errors that occur while trying to log the original error.
        logger.error(f"Error logging error for page {page_id}: {e}")

def get_parsed_pages(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches entries from `pages` with status='parsed'.

    These pages have been crawled and parsed, and are ready for
    LLM processing in the EXTRACT stage.

    Args:
        limit (int): Maximum number of records to return.

    Returns:
        List[Dict[str, Any]]: A list of parsed pages ready for EXTRACT.
    """
    try:
        if USE_SQLITE:
            return get_db().select("pages", where="status = ?", params=("parsed",), limit=limit)
        else:
            response = (
                supabase.table("pages")
                .select("*")
                .eq("status", "parsed")
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching parsed pages: {e}")
        return []


def get_unpromoted_pages() -> List[Dict[str, Any]]:
    """
    Fetches all entries from the `pages` table that have a status of 'parsed'.

    These are typically pages whose content has been successfully parsed and are ready
    for further processing, such as LLM classification.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a parsed page.
                              Returns an empty list if no parsed pages are found or an error occurs.
    """
    try:
        if USE_SQLITE:
            # For SQLite, just return parsed pages (no view available)
            return get_db().select("pages", where="status = ?", params=("parsed",))
        else:
            # query pages to get unpublished rows, which returns ~1000 rows
            response = supabase.table("vw_unpromoted_parsed_pages") \
                .select("*") \
                .execute()
            # get 200 random sample from the returned records
            sampled_rows = response.data

            return sampled_rows if sampled_rows else []

    except Exception as e:
        logger.error(f"Error fetching parsed pages: {e}")
        return []

def batch_update_status(page_ids: List[str], status: str, batch_size: int = 100) -> None:
    """
    Updates the status for a batch of pages in the `pages` table.

    Args:
        page_ids (List[str]): A list of unique identifiers (IDs) of the pages to update.
        status (str): The new status to assign to the pages.
        batch_size (int): The number of records to update in each chunk.
    """
    if not page_ids:
        return

    update_payload = {
        "status": status
    }

    for i in range(0, len(page_ids), batch_size):
        chunk = page_ids[i:i + batch_size]
        try:
            if USE_SQLITE:
                # Update using IN clause with parameter substitution
                placeholders = ", ".join("?" * len(chunk))
                query = f"UPDATE pages SET status = ?, updated_at = ? WHERE id IN ({placeholders})"
                get_db().execute_query(
                    query,
                    (status, datetime.utcnow().isoformat()) + tuple(chunk)
                )
                logger.info(f"Attempted to update {len(chunk)} pages to status '{status}'.")
            else:
                # Perform the update operation, setting the new status for all matching IDs.
                supabase.table("pages").update(update_payload).in_("id", chunk).execute()
                logger.info(f"Attempted to update {len(chunk)} pages to status '{status}'.")
        except Exception as e:
            # Log any errors that occur during the batch status update.
            logger.error(f"Error batch updating page statuses: {e}")
            raise


def update_page_extraction_failed(page_id: str, error_message: str, model_name: str = None) -> None:
    """
    Marks a page as failed during LLM extraction.

    Args:
        page_id (str): The unique identifier of the page.
        error_message (str): Description of the extraction error.
        model_name (str): The LLM model that was used.
    """
    update_payload = {
        "status": "extraction_failed",
        "error_type": "extraction_error",
        "error_message": error_message,
        "extract_model_name": model_name,
    }
    try:
        if USE_SQLITE:
            get_db().update("pages", update_payload, "id = ?", (page_id,))
            logger.info(f"Marked page {page_id} as extraction_failed.")
        else:
            supabase.table("pages").update(update_payload).eq("id", page_id).execute()
            logger.info(f"Marked page {page_id} as extraction_failed.")
    except Exception as e:
        logger.error(f"Error marking page {page_id} as extraction_failed: {e}")


def update_page_extract_results(
    page_id: str,
    is_film_review: bool,
    movie_names: str,
    sentiment: str,
    cleaned_title: str,
    cleaned_short_review: str,
    model_name: str = None
) -> None:
    """
    Updates a page with LLM extraction results.

    This function is called after LLM extraction to store the cleaned and
    categorized review data in the pages table.

    Args:
        page_id (str): The unique identifier of the page to update.
        is_film_review (bool): Whether the review is about a film.
        movie_names (str): JSON array string of movie names found in review.
        sentiment (str): Sentiment classification ('positive', 'negative', 'neutral').
        cleaned_title (str): Cleaned/standardized title text.
        cleaned_short_review (str): Cleaned/standardized short review text.
        model_name (str): The LLM model used for extraction (e.g., "anthropic/claude-sonnet-4-20250514").
    """
    update_payload = {
        "is_film_review": is_film_review,
        "movie_names": movie_names,
        "sentiment": sentiment,
        "cleaned_title": cleaned_title,
        "cleaned_short_review": cleaned_short_review,
        "extract_model_name": model_name,
        "status": "extracted",
        "extracted_at": datetime.utcnow().isoformat()
    }

    try:
        if USE_SQLITE:
            get_db().update("pages", update_payload, "id = ?", (page_id,))
            logger.info(f"Successfully updated page {page_id} with extraction results.")
        else:
            supabase.table("pages").update(update_payload).eq("id", page_id).execute()
            logger.info(f"Successfully updated page {page_id} with extraction results.")
    except Exception as e:
        logger.error(f"Error updating extraction results for page {page_id}: {e}")
        raise
