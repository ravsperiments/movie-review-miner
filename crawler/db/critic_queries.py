"""
Database queries for critic reference data.

This module provides access to critic metadata from the critics table,
including critic names, base URLs, biographical information, and timestamps.
"""

import logging
from typing import List, Dict, Any

try:
    from crawler.db.sqlite_client import get_db
    USE_SQLITE = True
except Exception:
    from crawler.db.supabase_client import supabase
    USE_SQLITE = False

logger = logging.getLogger(__name__)


def get_critics() -> List[Dict[str, Any]]:
    """
    Fetch all critic records from the critics table.

    Retrieves all critics with their metadata including ID, name, base URL,
    biography, and timestamp information.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing:
            - id: Unique identifier for the critic
            - name: Critic's name
            - base_url: Base URL of the critic's website
            - bio: Biographical information
            - created_at: Record creation timestamp
            - updated_at: Last update timestamp

            Returns an empty list if no critics are found or an error occurs.

    Raises:
        Logs error messages on exception but does not raise.
    """
    try:
        if USE_SQLITE:
            results = get_db().select("critics", "id, name, base_url, bio, created_at, updated_at")
            return results if results else []
        else:
            response = supabase.table("critics").select("id, name, base_url, bio, created_at, updated_at").execute()
            if response.data:
                return response.data
            return []
    except Exception as e:
        logger.error(f"Error fetching critics: {e}")
        return []
