
"""
This script orchestrates the reconciliation of LLM outputs for review classification.
It fetches parsed records, reconciles them, and updates their status in Supabase.
"""

import os
from dotenv import load_dotenv
from crawler.db.supabase_client import SupabaseClient
from crawler.llm.reconcile_llm_output.classify_review import (
    fetch_parsed_records,
    reconcile_classify_review,
    update_status,
    insert_clean_reviews,
)
from crawler.llm.reconcile_llm_output.utils import get_logger
from crawler.pipeline.classify_review_orchestrator import CLASSIFICATION_MODELS

# Load environment variables
load_dotenv()

# Configure logger
logger = get_logger(__name__)

# --- Configuration ---
PRIMARY_MODEL = CLASSIFICATION_MODELS["primary"]
JUDGE_MODEL = CLASSIFICATION_MODELS["judge"]

def main():
    """
    Main function to orchestrate the reconciliation process.
    """
    logger.info("Starting LLM output reconciliation process...")

    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        logger.error("Supabase URL and Key must be set in the environment variables.")
        return

    client = SupabaseClient(supabase_url, supabase_key)

    # 1. Fetch parsed records
    records = fetch_parsed_records(client, PRIMARY_MODEL, JUDGE_MODEL)
    if not records:
        logger.info("No parsed records to process.")
        return

    # 2. Reconcile LLM outputs
    promoted, not_promoted = reconcile_classify_review(records, PRIMARY_MODEL, JUDGE_MODEL)

    # 3. Update statuses and insert clean reviews in a transaction
    try:
        client.connection.transaction()
        
        # Update promoted records
        if promoted:
            promoted_ids = [r['source_id'] for r in promoted]
            update_status(client, promoted_ids, 'promoted')
            insert_clean_reviews(client, promoted)

        # Update not_promoted records
        if not_promoted:
            update_status(client, not_promoted, 'not_promoted')

        client.connection.commit()
        logger.info("Transaction committed successfully.")

    except Exception as e:
        client.connection.rollback()
        logger.error(f"Transaction failed: {e}. Changes rolled back.")

    logger.info("Reconciliation process finished.")

if __name__ == "__main__":
    main()

