"""Log pipeline step outcomes to Supabase."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .supabase_client import supabase
from ..utils.logger import get_logger

logger = get_logger(__name__)


def log_step_result(
    step_name: str,
    *,
    link_id: str | None = None,
    movie_id: str | None = None,
    attempt_number: int = 1,
    status: str,
    result_data: dict[str, Any] | None = None,
    error_message: str | None = None,
    timestamp: datetime | None = None,
) -> None:
    """Insert a pipeline step result into the ``pipeline_logs`` table."""
    data: dict[str, Any] = {
        "step_name": step_name,
        "attempt_number": attempt_number,
        "status": status,
    }
    if link_id is not None:
        data["link_id"] = link_id
    if movie_id is not None:
        data["movie_id"] = movie_id
    if timestamp:
        data["created_at"] = timestamp.isoformat()
    if result_data is not None:
        data["result_data"] = result_data
    if error_message is not None:
        data["error_message"] = error_message

    try:
        logger.debug("Logging pipeline step: %s", data)
        supabase.table("pipeline_logs").insert(data).execute()
    except Exception as e:
        logger.error("Failed to insert pipeline log: %s", e)
