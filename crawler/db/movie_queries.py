"""Database helpers for managing movie records."""

from datetime import datetime
import logging

try:
    from crawler.db.sqlite_client import get_db
    USE_SQLITE = True
except Exception:
    from crawler.db.supabase_client import supabase
    USE_SQLITE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_movie_by_title(title: str) -> dict | None:
    """Return a movie record by title if it exists."""
    try:
        if USE_SQLITE:
            results = get_db().select("movies", "id", where="title = ?", params=(title,), limit=1)
            return results[0] if results else None
        else:
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


def create_movie(title: str, source: str = "extracted") -> str:
    """Insert a new movie row and return its UUID.

    Args:
        title: The movie title.
        source: Data source - 'extracted' (from LLM), 'tmdb', 'manual', etc.
    """
    try:
        if USE_SQLITE:
            return get_db().insert("movies", {"title": title, "source": source})
        else:
            result = (
                supabase.table("movies")
                .insert({"title": title, "source": source})
                .execute()
            )
            return result.data[0]["id"]
    except Exception as e:
        logger.error("Failed to insert movie '%s': %s", title, e)
        raise


def update_movie_metadata(movie_id: str, metadata: dict, source: str = "tmdb"):
    """Update release year, language and genre for a movie.

    Args:
        movie_id: The movie's unique identifier.
        metadata: Dict with release_year, language, genre, popularity, poster_path.
        source: Data source - 'tmdb', 'manual', etc.
    """
    try:
        update = {
            "release_year": metadata.get("release_year"),
            "language": metadata.get("language"),
            "genre": metadata.get("genre"),
            "popularity": metadata.get("popularity"),
            "poster_path": metadata.get("poster_path"),
            "tmdb_id": metadata.get("tmdb_id"),
            "source": source,
        }
        if USE_SQLITE:
            get_db().update("movies", update, "id = ?", (movie_id,))
        else:
            supabase.table("movies").update(update).eq("id", movie_id).execute()
    except Exception as e:
        logger.error("Failed to update movie %s metadata: %s", movie_id, e)


def get_movies_pending_enrichment() -> list[dict]:
    """Return movies with status='pending_enrichment' for TMDB enrichment."""
    try:
        if USE_SQLITE:
            results = get_db().select(
                "movies",
                "id, title, release_year, language, genre",
                where="status = ?",
                params=("pending_enrichment",)
            )
            logger.info("Returned %s movies pending enrichment", len(results))
            return results
        else:
            result = (
                supabase.table("movies_with_review_year")
                .select("id, title, release_year, language, genre, review_year")
                .eq("status", "pending_enrichment")
                .execute()
            )
            logger.info("Returned %s movies pending enrichment", len(result.data))
            return result.data if result.data else []
    except Exception as e:
        logger.error("Failed to fetch movies pending enrichment: %s", e)
        return []


def get_movies_missing_metadata() -> list[dict]:
    """Return movies that do not yet have TMDb metadata (legacy - use get_movies_pending_enrichment)."""
    return get_movies_pending_enrichment()


def update_movie_status(movie_id: str, status: str, error_message: str = None) -> None:
    """
    Update a movie's status.

    Args:
        movie_id: The movie's unique identifier.
        status: New status ('pending_enrichment', 'enriched', 'enrichment_failed').
        error_message: Error details if status is 'enrichment_failed'.
    """
    try:
        update = {"status": status}
        if error_message:
            update["error_message"] = error_message

        if USE_SQLITE:
            get_db().update("movies", update, "id = ?", (movie_id,))
        else:
            supabase.table("movies").update(update).eq("id", movie_id).execute()
        logger.info(f"Updated movie {movie_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update movie {movie_id} status: {e}")
