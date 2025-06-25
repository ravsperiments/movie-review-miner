"""Utility script for enriching reviews with TMDb metadata."""

import os
import requests
from dotenv import load_dotenv
from supabase import create_client

from utils.logger import get_logger

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

logger = get_logger(__name__)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error("Failed to create Supabase client: %s", e)
    raise


def fetch_unenriched_reviews():
    """Return reviews that have not yet been enriched with TMDb data."""
    try:
        response = (
            supabase.table("reviews")
            .select("id, movie_title")
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error("Failed to fetch unenriched reviews: %s", e)
        return []


def search_tmdb(movie_title: str) -> dict | None:
    """Search TMDb for movie metadata by title."""
    url = f"{TMDB_BASE_URL}/search/movie"
    headers = {
        "Authorization": f"Bearer {TMDB_API_KEY}",
        "Content-Type": "application/json;charset=utf-8",
    }
    params = {"query": movie_title}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error("TMDb request failed for %s: %s", movie_title, e)
        return None

    if not data.get("results"):
        logger.warning("No TMDb results for %s", movie_title)
        return None

    top_result = data["results"][0]
    return {
        "release_year": top_result.get("release_date", "")[:4],
        "language": top_result.get("original_language", ""),
        "genre_ids": top_result.get("genre_ids", []),
    }


def update_metadata(record_id: str, metadata: dict) -> None:
    """Persist TMDb metadata to the ``reviews`` table."""
    update = {
        "release_year": metadata.get("release_year") or None,
        "language": metadata.get("language"),
        "genre": ", ".join(str(g) for g in metadata.get("genre_ids", [])),
    }
    try:
        supabase.table("reviews").update(update).eq("id", record_id).execute()
    except Exception as e:
        logger.error("Failed to update metadata for %s: %s", record_id, e)


def main():
    """Entry point: enrich all reviews missing TMDb data."""
    reviews = fetch_unenriched_reviews()
    logger.info("Found %s unenriched reviews", len(reviews))

    for review in reviews:
        movie_title = review.get("movie_title")
        try:
            logger.info("Processing: %s", movie_title)
            metadata = search_tmdb(movie_title)
            logger.debug("Metadata: %s", metadata)
            if metadata:
                update_metadata(review["id"], metadata)
                logger.info("Updated Supabase for %s", movie_title)
            else:
                logger.warning("No metadata found for %s", movie_title)
        except Exception as e:
            logger.error("Skipped %s: %s", movie_title, e)


if __name__ == "__main__":
    main()
