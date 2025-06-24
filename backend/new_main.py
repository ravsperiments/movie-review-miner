import os
from supabase import create_client
import requests
from dotenv import load_dotenv

from utils.logger import get_logger

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


logger = get_logger(__name__)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error("Failed to create Supabase client: %s", e)
    raise

def fetch_unenriched_reviews():
    try:
        response = (
            supabase
            .table("reviews")
            .select("id, movie_title")
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error("Failed to fetch unenriched reviews: %s", e)
        return []


def search_tmdb(movie_title: str) -> dict | None:
    """Search TMDb for movie metadata by title using v4 Bearer token."""
    url = "https://api.themoviedb.org/3/search/movie"
    headers = {
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY')}",
        "Content-Type": "application/json;charset=utf-8"
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
        "genre_ids": ", ".join([g["name"] for g in data.get("genres", [])])
    }

def update_metadata(record_id, metadata):
    update = {
        "release_year": metadata.get("release_date", "")[:4] or None,
        "language": metadata.get("original_language"),
        "genre": ", ".join(str(genre_id) for genre_id in metadata.get("genre_ids", []))
    }
    try:
        supabase.table("reviews").update(update).eq("id", record_id).execute()
    except Exception as e:
        logger.error("Failed to update metadata for %s: %s", record_id, e)

def main():
    reviews = fetch_unenriched_reviews()
    logger.info("Found %s unenriched reviews", len(reviews))

    for review in reviews:
        try:
            logger.info("Processing: %s", review['movie_title'])
            metadata = search_tmdb(review['movie_title'])
            logger.debug("Metadata: %s", metadata)
            update_metadata(review['id'], metadata)
            logger.info("Updated Supabase for %s", review['movie_title'])
        except Exception as e:
            logger.error("Skipped %s: %s", review.get('movie_title'), e)

if __name__ == "__main__":
    main()
