"""Step 6: use TMDb to enrich movie metadata."""
import asyncio
from db.movie_queries import get_movies_missing_metadata, update_movie_metadata
from tmdb.tmdb_api import search_tmdb
from utils.logger import get_logger
from tqdm import tqdm

logger = get_logger(__name__)

async def enrich_metadata() -> None:
    """Fill in metadata for movies lacking it using TMDb."""
    movies = get_movies_missing_metadata()
    logger.info("Enriching metadata for %s movies", len(movies))

    for movie in tqdm(movies):
        try:
            metadata = await search_tmdb(movie["title"])
            if metadata:
                update_movie_metadata(movie["id"], metadata)
                logger.info("Updated metadata for %s", movie["title"])
            else:
                logger.warning("No metadata found for %s", movie["title"])
        except Exception as e:
            logger.error("TMDb enrichment failed for %s: %s", movie.get("title"), e)
