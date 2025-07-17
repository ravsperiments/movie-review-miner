"""
Database operations for the stg_clean_reviews table.
"""
import logging
from typing import List, Dict, Any
from crawler.db.supabase_client import supabase

logger = logging.getLogger(__name__)

def batch_insert_clean_reviews(records: List[Dict[str, Any]]) -> None:
    """
    Batch inserts reconciled records into the stg_clean_reviews table.
    Can run within a transaction if a client is provided.

    Args:
        records (List[Dict[str, Any]]): List of promoted review records.
        client: Optional Supabase client instance for transactional operations.
    """
    if not records:
        return

    batch_data = [
        {
            "raw_page_id": record["source_id"],
            "movie_name": record["movie_name"],
            "sentiment": record["sentiment"],
        }
        for record in records
    ]

    try:
        # The actual execution happens here, using the appropriate client.
        supabase.table("stg_clean_reviews").insert(batch_data).execute()
        logger.info(f"Attempted to insert {len(batch_data)} clean reviews.")
    except Exception as e:
        logger.error(f"Error during batch insert of clean reviews: {e}")
        raise
