import logging
from typing import List, Dict, Any

from crawler.db.supabase_client import supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_staged_reviews(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches a specified number of records from the `vw_staged_reviews` view.

    Args:
        limit (int): The maximum number of records to return.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a staged review.
                              Returns an empty list if no records are found or an error occurs.
    """
    try:
        response = supabase.table("vw_staged_reviews").select("*").limit(limit).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching staged reviews: {e}")
        return []

def update_cleaned_review_fields(raw_page_id: str, cleaned_title: str, cleaned_short_review: str) -> bool:
    """
    Updates the cleaned_title and cleaned_short_review fields for a specific review.

    Args:
        raw_page_id (str): The raw_page_id to identify the review
        cleaned_title (str): The cleaned title text
        cleaned_short_review (str): The cleaned short review text

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table("stg_clean_reviews").update({
            "cleaned_title": cleaned_title,
            "cleaned_short_review": cleaned_short_review
        }).eq("raw_page_id", raw_page_id).execute()
        
        if response.data:
            logger.info(f"Successfully updated cleaned fields for raw_page_id: {raw_page_id}")
            return True
        else:
            logger.warning(f"No rows updated for raw_page_id: {raw_page_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating cleaned fields for raw_page_id {raw_page_id}: {e}")
        return False

def batch_insert_clean_reviews(records: List[Dict[str, Any]]) -> bool:
    """
    Batch inserts clean review records into stg_clean_reviews.
    
    Args:
        records: List of dictionaries with clean review data
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not records:
        logger.warning("No records provided for batch insert.")
        return False
        
    try:
        # Transform records to match database schema
        insert_data = []
        for record in records:
            insert_data.append({
                "raw_page_id": record["raw_page_id"],
                "cleaned_title": record["cleaned_title"],
                "cleaned_short_review": record["cleaned_short_review"],
                "is_title_valid": record.get("is_title_valid"),
                "is_short_review_valid": record.get("is_short_review_valid"),
                "status": record.get("status", "approved")
            })
        
        response = supabase.table("stg_clean_reviews").insert(insert_data).execute()
        
        if response.data:
            logger.info(f"Successfully batch inserted {len(insert_data)} clean review records.")
            return True
        else:
            logger.error("Batch insert returned no data.")
            return False
            
    except Exception as e:
        logger.error(f"Error batch inserting clean review records: {e}")
        return False

def batch_update_clean_review_status(source_ids: List[str], status: str) -> bool:
    """
    Batch updates the status of clean review records.
    
    Args:
        source_ids: List of raw_page_ids to update
        status: New status value
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not source_ids:
        logger.warning("No source_ids provided for batch status update.")
        return False
        
    try:
        response = supabase.table("stg_clean_reviews").update({
            "status": status
        }).in_("raw_page_id", source_ids).execute()
        
        if response.data:
            logger.info(f"Successfully updated status to '{status}' for {len(source_ids)} records.")
            return True
        else:
            logger.warning(f"No records updated for status '{status}'.")
            return False
            
    except Exception as e:
        logger.error(f"Error batch updating clean review status to '{status}': {e}")
        return False