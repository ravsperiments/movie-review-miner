import uuid
from datetime import datetime, timezone
import json
import hashlib

from crawler.db.supabase_client import supabase

def insert_llm_log(
    source_table: str,
    source_id: uuid.UUID,
    model_name: str,
    task_type: str,
    input_data: dict,
    output_raw: str,
    output_parsed: dict,
    task_fingerprint: str,
    accepted: bool = None
):
    """
    Inserts a log entry into the stg_llm_logs table.
    """
    data = {
        "source_table": source_table,
        "source_id": str(source_id),
        "model_name": model_name,
        "task_type": task_type,
        "input": json.dumps(input_data),
        "output_raw": output_raw,
        "output_parsed": json.dumps(output_parsed),
        "task_fingerprint": task_fingerprint,
        "accepted": accepted,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    try:
        supabase.table("stg_llm_logs").insert(data).execute()
        print(f"Successfully inserted LLM log for source_id: {source_id}, model: {model_name}")
    except Exception as e:
        print(f"Error inserting LLM log for source_id: {source_id}, model: {model_name}: {e}")
        raise

def generate_task_fingerprint(task_type: str, source_id: uuid.UUID) -> str:
    """
    Generates a SHA256 hash of task_type + source_id for deduplication.
    The fingerprint will be identical for the same source_id and task_type.
    """
    combined_string = f"{task_type}-{source_id}"
    return hashlib.sha256(combined_string.encode('utf-8')).hexdigest()

def batch_insert_llm_logs(rows: list[dict]) -> None:
    """
    Batch insert multiple LLM log entries into stg_llm_logs.
    Each row dict must contain:
      source_table, source_id, model_name, task_type,
      input_data, task_fingerprint, output_raw, accepted
    """
    now = datetime.now(timezone.utc).isoformat()
    batch = []
    for row in rows:
        batch.append({
            "source_table": row["source_table"],
            "source_id": str(row["source_id"]),
            "model_name": row["model_name"],
            "task_type": row["task_type"],
            "input": json.dumps(row["input_data"], sort_keys=True),
            "output_raw": row["output_raw"],
            # Classification fields (optional)
            "is_movie_review": json.dumps(row.get("is_movie_review"), sort_keys=True) if row.get("is_movie_review") is not None else None,
            "sentiment": row.get("sentiment"),
            "movie_name": row.get("movie_name"),
            # Clean review fields (optional)
            "cleaned_title": row.get("cleaned_title"),
            "cleaned_short_review": row.get("cleaned_short_review"),
            "is_title_valid": row.get("is_title_valid"),
            "is_short_review_valid": row.get("is_short_review_valid"),
            "task_fingerprint": row["task_fingerprint"],
            "accepted": row.get("accepted"),
            "created_at": now,
        })
    supabase.table("stg_llm_logs").insert(batch).execute()

def get_reconciliation_records(primary_model: str, judge_model: str, task_type: str = None) -> list:
    """
    Fetches records for reconciliation from the database.
    
    Args:
        primary_model: Name of the primary model
        judge_model: Name of the judge model  
        task_type: Optional task type filter
    """
    try:
        if task_type:
            # For clean review, we need a simpler approach since we have different task types
            response = supabase.table("stg_llm_logs").select("*").eq("task_type", task_type).execute()
            return response.data
        else:
            # Use the existing RPC for classification reconciliation
            response = supabase.rpc(
                'get_reconciliation_data',
                {
                    'p_primary_model': primary_model,
                    'p_judge_model': judge_model
                }
            ).execute()
            return response.data
    except Exception as e:
        print(f"Error fetching reconciliation records: {e}")
        return []

def get_latest_clean_review_output(source_id: str, model_name: str) -> dict:
    """
    Gets the latest cleaned review output for a specific source_id and model.
    
    Args:
        source_id: The source_id to find
        model_name: The model name to filter by
        
    Returns:
        dict: The cleaned content or empty dict if not found
    """
    try:
        response = supabase.table("stg_llm_logs").select("cleaned_title, cleaned_short_review").eq(
            "source_id", source_id
        ).eq(
            "model_name", model_name
        ).eq(
            "task_type", "clean_review"
        ).eq(
            "accepted", True
        ).order("created_at", desc=True).limit(1).execute()
        
        if response.data:
            return response.data[0]
        else:
            return {}
    except Exception as e:
        print(f"Error fetching latest clean review output: {e}")
        return {}
