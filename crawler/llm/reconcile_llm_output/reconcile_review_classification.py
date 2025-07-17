"""
This module handles the reconciliation of LLM outputs for review classification.
"""
import logging
from crawler.db.llm_log_queries import get_reconciliation_records
from crawler.db.scraper_queries import batch_update_status
from crawler.db.stg_clean_review_queries import batch_insert_clean_reviews

# Configure logger
logger = logging.getLogger(__name__)

def run_reconciliation_pipeline(primary_model: str, judge_model: str):
    """
    Orchestrates the entire reconciliation process.
    """

    # 1. Fetch records
    logger.info("Fetching parsed records for reconciliation...")
    records = _fetch_parsed_records(primary_model, judge_model)
    if not records:
        logger.info("No records to reconcile. Exiting reconciliation pipeline.")
        return
    logger.info(f"Successfully fetched {len(records)} records for reconciliation.")

    # 2. Reconcile records
    logger.info("Reconciling LLM outputs...")
    promoted, not_promoted = _reconcile_classify_review(records, primary_model, judge_model)
    logger.info(f"Reconciliation resulted in {len(promoted)} promoted and {len(not_promoted)} not_promoted records.")

    # 3. Execute database updates
    try:
        logger.info("Updating database with reconciliation results...")
        if promoted:
            promoted_ids = [r["source_id"] for r in promoted]
            logger.info(f"Updating status to 'promoted' for {len(promoted_ids)} records.")
            _update_status(promoted_ids, "promoted")
            logger.info(f"Inserting {len(promoted)} clean reviews.")
            _insert_clean_reviews(promoted)
        else:
            logger.info("No records to promote.")

        if not_promoted:
            logger.info(f"Updating status to 'not_promoted' for {len(not_promoted)} records.")
            _update_status(not_promoted, "not_promoted")
        else:
            logger.info("No records to mark as not_promoted.")

        logger.info("Database updates completed successfully.")
    except Exception as e:
        logger.error(f"Error during database updates in reconciliation: {e}")

    logger.info("Reconciliation pipeline finished.")

def _fetch_parsed_records(primary_model: str, judge_model: str):
    """
    Fetches and reshapes parsed records from Supabase.
    """
    try:
        raw_records = get_reconciliation_records(primary_model, judge_model)

        reshaped_records = []
        primary_model_key = f"{primary_model.replace('-', '_')}_output"
        judge_model_key = f"{judge_model.replace('-', '_')}_output"

        for record in raw_records:
            record[primary_model_key] = record.pop('primary_output', None)
            record[judge_model_key] = record.pop('judge_output', None)
            reshaped_records.append(record)
        logger.debug(f"Reshaped {len(reshaped_records)} records.")
        return reshaped_records
    except Exception as e:
        logger.error(f"Error fetching and reshaping parsed records: {e}")
        return []

def _reconcile_classify_review(records: list, primary_model: str, judge_model: str):
    """
    Reconciles the outputs from different LLM models.
    """
    promoted = []
    not_promoted = []
    skipped = []

    primary_model_key = f"{primary_model.replace('-', '_')}_output"
    judge_model_key = f"{judge_model.replace('-', '_')}_output"

    for record in records:
        primary_output = str(record.get(primary_model_key, '')).lower() or None
        judge_output = str(record.get(judge_model_key, '')).lower() or None

        if not primary_output and not judge_output:
            skipped.append(record['source_id'])
            continue

        if judge_output == 'true':
            promoted.append(record)
        elif primary_output == 'true' and judge_output != 'false':
            promoted.append(record)
        else:
            not_promoted.append(record['source_id'])
    return promoted, not_promoted

def _update_status(source_ids: list, status: str):
    """
    Updates the status of records in raw_scrapped_pages.
    """
    if not source_ids:
        logger.info(f"No source_ids provided for status update to '{status}'.")
        return
    try:
        batch_update_status(source_ids, status)
    except Exception as e:
        logger.error(f"Error updating status to '{status}': {e}")
        raise

def _insert_clean_reviews(records: list):
    """
    Inserts reconciled records into stg_clean_reviews.
    """
    if not records:
        logger.info("No records to insert into stg_clean_reviews.")
        return

    valid_records = [r for r in records if r.get('movie_name') and r.get('sentiment')]
    if len(valid_records) != len(records):
        logger.warning(f"Skipping {len(records) - len(valid_records)} records due to missing movie_name or sentiment.")

    if not valid_records:
        logger.info("No valid records to insert into stg_clean_reviews after validation.")
        return

    try:
        batch_insert_clean_reviews(valid_records)
    except Exception as e:
        logger.error(f"Error inserting clean reviews: {e}")
        raise
