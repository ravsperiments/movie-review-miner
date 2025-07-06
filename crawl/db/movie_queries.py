
"""Database helpers for managing movie records in Supabase."""

from datetime import datetime
from db.supabase_client import supabase
from utils.logger import get_logger

logger = get_logger(__name__)

def get_movie_by_title(title: str) -> dict | None:
    """Return a movie record by title if it exists."""
    try:
        result = (
            supabase.table("movies")
            .select("id")
            .eq("title", title)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Error querying movie title '%s': %s", title, e)
        return None

def create_movie(title: str) -> str:
    """Insert a new movie row and return its UUID."""
    try:
        result = (
            supabase.table("movies")
            .insert({"title": title})
            .execute()
        )
        return result.data[0]["id"]
    except Exception as e:
        logger.error("Failed to insert movie '%s': %s", title, e)
        raise

def update_movie_metadata(movie_id: str, metadata: dict):
    """Update release year, language and genre for a movie."""
    try:
        update = {
            "release_year": metadata.get("release_year"),
            "language": metadata.get("language"),
            "genre": metadata.get("genre"),
            "popularity": metadata.get("popularity"),
            "poster_path": metadata.get("poster_path")
        }
        supabase.table("movies").update(update).eq("id", movie_id).execute()
    except Exception as e:
        logger.error("Failed to update movie %s metadata: %s", movie_id, e)


def get_movies_missing_metadata() -> list[dict]:
    """Return movies that do not yet have TMDb metadata."""
    try:
        result = (
            supabase.table("movies_with_review_year")
            .select("id, title, release_year, language, genre, review_year")
            .is_("release_year", None)
            .execute()
        )
        print(f"Returned %s movies without metadata", len(result.data))
        logger.info("Returned %s movies without metadata", len(result.data))
        return [r for r in result.data if not r.get("release_year")]
    except Exception as e:
        logger.error("Failed to fetch movies without metadata: %s", e)
        return []
