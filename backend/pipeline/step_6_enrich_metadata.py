"""Step 6: use TMDb to enrich movie metadata."""
import asyncio
from db.movie_queries import get_movies_missing_metadata, update_movie_metadata
from db.review_queries import get_post_date_for_movie
from tmdb.tmdb_api import search_tmdb
from utils.logger import get_logger
from utils.io_helpers import write_failure
from tqdm import tqdm

logger = get_logger(__name__)

CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _enrich_movie(movie: dict) -> None:
    try:
        async with semaphore:
            metadata = await search_tmdb(movie["title"], movie["year"])
        if metadata:
            update_movie_metadata(movie["id"], metadata)
            logger.info("Updated metadata for %s", movie["title"])
        else:
            logger.warning("No metadata found for %s", movie["title"])
    except Exception as e:
        logger.error(
            "TMDb enrichment failed for %s: %s", movie.get("title"), e, exc_info=True
        )
        write_failure("failed_tmdb.txt", movie.get("title", ""), e)


async def enrich_metadata() -> None:
    """Fill in metadata for movies lacking it using TMDb."""
    movies = get_movies_missing_metadata()
    logger.info("Enriching metadata for %s movies", len(movies))

    for movie in movies:
        post_date = get_post_date_for_movie(movie["id"])
        year = post_date["post_date"][:4] if post_date else None

        #  enrich the dict itself
        movie["year"] = year

    tasks = [_enrich_movie(movie) for movie in movies]
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Metadata enrichment complete")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(enrich_metadata())