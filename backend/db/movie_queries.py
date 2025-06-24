
from datetime import datetime
from db.supabase_client import supabase
from utils.logger import get_logger

logger = get_logger(__name__)

def get_movie_by_title(title: str) -> dict | None:
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
    try:
        update = {
            "release_year": metadata.get("release_year"),
            "language": metadata.get("language"),
            "genre": metadata.get("genre"),
        }
        supabase.table("movies").update(update).eq("id", movie_id).execute()
    except Exception as e:
        logger.error("Failed to update movie %s metadata: %s", movie_id, e)
