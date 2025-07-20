"""
This module handles the reconciliation of LLM outputs for review cleaning.
"""
import logging
from crawler.db.llm_log_queries import get_reconciliation_records
from crawler.db.stg_clean_review_queries import batch_insert_clean_reviews, batch_update_clean_review_status

# Configure logger
logger = logging.getLogger(__name__)

def run_clean_review_reconciliation_pipeline(primary_model: str, judge_model: str):
    """
    Orchestrates the entire reconciliation process for clean review tasks.
    """

    # 1. Fetch records
    logger.info("Fetching clean review records for reconciliation...")
    records = _fetch_clean_review_records(primary_model, judge_model)
    if not records:
        logger.info("No clean review records to reconcile. Exiting reconciliation pipeline.")
        return
    logger.info(f"Successfully fetched {len(records)} clean review records for reconciliation.")

    # 2. Reconcile records
    logger.info("Reconciling clean review LLM outputs...")
    approved, rejected = _reconcile_clean_review_outputs(records, primary_model, judge_model)
    logger.info(f"Reconciliation resulted in {len(approved)} approved and {len(rejected)} rejected records.")

    # 3. Execute database updates
    try:
        logger.info("Updating database with clean review reconciliation results...")
        
        if approved:
            approved_data = [r for r in approved if _validate_clean_review_data(r)]
            if approved_data:
                logger.info(f"Updating stg_clean_reviews with {len(approved_data)} approved records.")
                _insert_approved_clean_reviews(approved_data)
                _update_clean_review_status([r["source_id"] for r in approved_data], "approved")
            else:
                logger.warning("No valid approved records to insert after validation.")
        else:
            logger.info("No records approved for insertion.")

        if rejected:
            logger.info(f"Marking {len(rejected)} records as rejected.")
            _update_clean_review_status(rejected, "rejected")
        else:
            logger.info("No records to mark as rejected.")

        logger.info("Clean review reconciliation database updates completed successfully.")
    except Exception as e:
        logger.error(f"Error during database updates in clean review reconciliation: {e}")

    logger.info("Clean review reconciliation pipeline finished.")

def _fetch_clean_review_records(primary_model: str, judge_model: str):
    """
    Fetches and reshapes clean review records from the LLM logs.
    """
    try:
        # Fetch records for both task types
        primary_records = get_reconciliation_records(
            primary_model, judge_model, task_type="clean_review"
        )
        judge_records = get_reconciliation_records(
            primary_model, judge_model, task_type="judge_review"
        )
        
        # Group records by source_id
        records_by_source = {}
        
        # Process primary model outputs
        for record in primary_records:
            source_id = record["source_id"]
            if source_id not in records_by_source:
                records_by_source[source_id] = {"source_id": source_id}
            records_by_source[source_id]["primary_output"] = record.get("primary_output")
            records_by_source[source_id]["primary_data"] = record
        
        # Process judge model outputs
        for record in judge_records:
            source_id = record["source_id"]
            if source_id not in records_by_source:
                records_by_source[source_id] = {"source_id": source_id}
            records_by_source[source_id]["judge_output"] = record.get("judge_output")
            records_by_source[source_id]["judge_data"] = record
        
        # Convert to list and filter complete records
        complete_records = []
        for source_id, record in records_by_source.items():
            if "primary_output" in record and "judge_output" in record:
                complete_records.append(record)
            else:
                logger.warning(f"Incomplete record for source_id {source_id} - missing primary or judge output")
        
        logger.info(f"Found {len(complete_records)} complete records with both primary and judge outputs.")
        return complete_records
        
    except Exception as e:
        logger.error(f"Error fetching and reshaping clean review records: {e}")
        return []

def _reconcile_clean_review_outputs(records: list, primary_model: str, judge_model: str):
    """
    Reconciles the outputs from primary cleaning and judge assessment.
    For clean reviews: Primary does the work, Judge determines if it passes quality criteria.
    """
    approved = []
    rejected = []
    
    for record in records:
        source_id = record["source_id"]
        primary_data = record.get("primary_data", {})
        judge_data = record.get("judge_data", {})
        
        # Extract judge assessment
        title_valid = None
        short_review_valid = None
        try:
            judge_output = judge_data.get("judge_output", {})
            if isinstance(judge_output, dict):
                title_valid = judge_output.get("is_title_valid")
                short_review_valid = judge_output.get("is_short_review_valid")
            elif isinstance(judge_output, str):
                # Try to parse if it's a string representation
                import json
                judge_parsed = json.loads(judge_output)
                title_valid = judge_parsed.get("is_title_valid")
                short_review_valid = judge_parsed.get("is_short_review_valid")
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse judge output for source_id {source_id}")
        
        # Extract primary cleaning results
        primary_cleaned = None
        try:
            primary_output = primary_data.get("primary_output", {})
            if isinstance(primary_output, dict):
                primary_cleaned = primary_output
            elif isinstance(primary_output, str):
                # Try to parse if it's a string representation
                import json
                primary_cleaned = json.loads(primary_output)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse primary output for source_id {source_id}")
        
        # Decision logic: Both title and short review must be valid for approval
        if title_valid is True and short_review_valid is True and primary_cleaned:
            # Combine the data for approved records
            approved_record = {
                "source_id": source_id,
                "cleaned_title": primary_cleaned.get("cleaned_title"),
                "cleaned_short_review": primary_cleaned.get("cleaned_short_review"),
                "is_title_valid": title_valid,
                "is_short_review_valid": short_review_valid,
                "primary_data": primary_data,
                "judge_data": judge_data
            }
            approved.append(approved_record)
            logger.debug(f"Approved source_id {source_id} - both title and short review are valid")
        else:
            rejected.append(source_id)
            reasons = []
            if title_valid is not True:
                reasons.append("title invalid")
            if short_review_valid is not True:
                reasons.append("short review invalid")
            if not primary_cleaned:
                reasons.append("missing primary data")
            reason = ", ".join(reasons) if reasons else "unknown"
            logger.debug(f"Rejected source_id {source_id} - {reason}")
    
    return approved, rejected

def _validate_clean_review_data(record: dict) -> bool:
    """
    Validates that a clean review record has required fields.
    """
    required_fields = ["cleaned_title", "cleaned_short_review"]
    for field in required_fields:
        if not record.get(field) or not record[field].strip():
            logger.warning(f"Invalid record - missing or empty {field} for source_id {record.get('source_id')}")
            return False
    return True

def _insert_approved_clean_reviews(records: list):
    """
    Inserts approved clean review records into stg_clean_reviews.
    """
    if not records:
        logger.info("No approved clean review records to insert.")
        return

    try:
        # Transform records to match the expected format for batch_insert_clean_reviews
        clean_review_records = []
        for record in records:
            clean_review_records.append({
                "raw_page_id": record["source_id"],
                "cleaned_title": record["cleaned_title"],
                "cleaned_short_review": record["cleaned_short_review"],
                "is_title_valid": record.get("is_title_valid"),
                "is_short_review_valid": record.get("is_short_review_valid"),
                "status": "approved"
            })
        
        batch_insert_clean_reviews(clean_review_records)
        logger.info(f"Successfully inserted {len(clean_review_records)} approved clean reviews.")
        
    except Exception as e:
        logger.error(f"Error inserting approved clean reviews: {e}")
        raise

def _update_clean_review_status(source_ids: list, status: str):
    """
    Updates the status of clean review records.
    """
    if not source_ids:
        logger.info(f"No source_ids provided for clean review status update to '{status}'.")
        return
    try:
        batch_update_clean_review_status(source_ids, status)
        logger.info(f"Updated status to '{status}' for {len(source_ids)} clean review records.")
    except Exception as e:
        logger.error(f"Error updating clean review status to '{status}': {e}")
        raise