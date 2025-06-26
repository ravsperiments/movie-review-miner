"""Helper functions for persisting reviews to Supabase."""

from db.supabase_client import supabase
from utils.logger import get_logger

# Logger for database interactions
logger = get_logger(__name__)


def store_blog_post_urls(blog_post_urls: dict) -> None:
    """Insert a blog_post urls into the ``reviews`` table.

    Args:
        review: Dictionary containing the review data to persist.
    """
    try:
        logger.debug(
            "Inserting review: %s", {k: str(v)[:50] for k, v in blog_post_urls.items()}
        )
        response = supabase.table("reviews").insert(blog_post_urls).execute()
        logger.info("Insert successful: %s", response)
    except Exception as e:
        logger.error("DB Insert failed: %s", e)
        raise

def store_review_if_missing(review: dict) -> None:
    """Insert review only if the link does not already exist."""
    try:
        exists = (
            supabase.table("reviews")
            .select("id")
            .eq("link", review["link"])
            .is_("blog_title", None)
            .execute()
        )
        if exists.data:
            logger.info("Review already stored for %s", review["link"])
            return
        store_review(review)
    except Exception as e:
        logger.error("Store review check failed for %s: %s", review.get("link"), e)
        raise
