"""Helper functions for persisting reviews to Supabase."""

from db.supabase_client import supabase
from utils.logger import get_logger

# Logger for database interactions
logger = get_logger(__name__)


def store_review(review: dict) -> None:
    """Insert a parsed review into the ``reviews`` table.

    Args:
        review: Dictionary containing the review data to persist.
    """
    try:
        logger.debug(
            "Inserting review: %s", {k: str(v)[:50] for k, v in review.items()}
        )
        response = supabase.table("reviews").insert(review).execute()
        logger.info("Insert successful: %s", response)
    except Exception as e:
        logger.error("DB Insert failed: %s", e)
        raise
