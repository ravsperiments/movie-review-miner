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
        response = supabase.table("stg_llm_logs").insert(data).execute()
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
      input_data, task_fingerprint, output_raw, output_parsed, accepted
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
            "output_parsed": json.dumps(row["output_parsed"], sort_keys=True),
            "task_fingerprint": row["task_fingerprint"],
            "accepted": row.get("accepted"),
            "created_at": now,
        })
    supabase.table("stg_llm_logs").insert(batch).execute()
