"""Query helpers for interacting with review rows in Supabase."""

from datetime import datetime
from .supabase_client import supabase
from utils.logger import get_logger

logger = get_logger(__name__)

def get_latest_post_date() -> datetime | None:
    """Fetch the most recent post_date stored in Supabase."""
    try:
        result = supabase.table("reviews") \
            .select("post_date") \
            .order("post_date", desc=True) \
            .limit(1) \
            .execute()
        
        latest_post_date_str = result.data[0]["post_date"] if result.data else None
        if latest_post_date_str:
            return datetime.strptime(latest_post_date_str, "%Y-%m-%d")
    except Exception as e:
        logger.error("Failed to fetch latest post_date: %s", e)
    return None


def get_recent_links() -> set[str]:
    """
    Fetch all review links from Supabase where post_date >= min_post_date.

    Args:
        min_post_date: The cutoff date for filtering reviews.

    Returns:
        A set of URLs (strings).
    """
    try:
        result = (
            supabase.table("recent_review_links")
            .select("link, post_date")
            .execute()
        )
        return {r["link"] for r in result.data if "link" in r}
    except Exception as e:
        logger.error("Failed to fetch recent links", e)
        return set()
    
def get_links_without_movieid() -> list[dict]:
    """
    Fetch all reviews from Supabase where movie_id is null.

    Returns:
        A list of dicts with keys 'id', 'link', and 'blog_title'.
    """
    try:
        result = (
            supabase.table("reviews")
            .select("id, link, blog_title, movie_id")
            .is_("movie_id", None)
            .eq("is_film_review", True)
            .execute()
        )
        return [
            {
                "id": r["id"],
                "link": r["link"],
                "blog_title": r.get("blog_title", "")
            }
            for r in result.data
            if "id" in r and "link" in r
        ]
    except Exception as e:
        logger.error("Failed to fetch links without moview id: %s", e)
        return []

def update_review_with_movie_id(review_id: str, movie_id: str):
    """Update review with associated movie UUID."""
    try:
        supabase.table("reviews").update({"movie_id": movie_id}).eq("id", review_id).execute()
    except Exception as e:
        logger.error("Failed to update review %s with movie_id %s: %s", review_id, movie_id, e)

def get_reviews_missing_sentiment() -> list[dict]:
    """Fetch all reviews that do not yet have sentiment."""
    try:
        result = (
            supabase.table("reviews")
            .select("id, blog_title, short_review, sentiment")
            .is_('sentiment', None)
            .eq("is_film_review", True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("Failed to fetch reviews without sentiment: %s", e)
        return []

def update_sentiment_for_review(review_id: str, sentiment: str):
    """Update the sentiment for a given review ID."""
    try:
        supabase.table("reviews").update({"sentiment": sentiment}).eq("id", review_id).execute()
    except Exception as e:
        logger.error("Failed to update sentiment for review %s: %s", review_id, e)


def get_unclassified_reviews() -> list[dict]:
    """Return reviews without an is_film_review flag."""
    try:
        result = (
            supabase.table("reviews")
            .select("id, blog_title, short_review")
            .is_("is_film_review", None)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("Failed to fetch unclassified reviews: %s", e)
        return []


def update_is_film_review(review_id: str, value: bool) -> None:
    """Persist the is_film_review flag for a review."""
    try:
        supabase.table("reviews").update({"is_film_review": value}).eq("id", review_id).execute()
    except Exception as e:
        logger.error("Failed to update is_film_review for %s: %s", review_id, e)


def get_post_date_for_movie(movie_id: str) -> dict | None:
    result = (
        supabase.table("reviews")
        .select("id, post_date")
        .eq("movie_id", movie_id)
        .order("post_date", desc=False)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_links_with_title_tbd() -> list[dict]:
    result = (
        supabase.table("reviews")
        .select("id, link")
        .eq("blog_title", "TBD")
        .execute()
    )
    return result.data if result.data else None

