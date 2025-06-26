"""Step 6: use TMDb to enrich movie metadata."""
import asyncio
from db.movie_queries import get_movies_missing_metadata, update_movie_metadata
from db.review_queries import get_post_date_for_movie
from tmdb.tmdb_api import search_tmdb
from utils.logger import StepLogger
from utils.io_helpers import write_failure
from tqdm import tqdm

CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _enrich_movie(movie: dict, slog: StepLogger) -> None:
    try:
        async with semaphore:
            metadata = await search_tmdb(movie["title"], movie["review_year"])
        if metadata:
            update_movie_metadata(movie["id"], metadata)
            slog.logger.info("Updated metadata for %s", movie["title"])
            slog.processed()
            slog.saved()
        else:
            slog.logger.warning("No metadata found for %s", movie["title"])
            slog.processed()
    except Exception as e:
        slog.logger.error(
            "TMDb enrichment failed for %s: %s", movie.get("title"), e, exc_info=True
        )
        slog.processed()
        slog.failed()
        write_failure("failed_tmdb.txt", movie.get("title", ""), e)


async def enrich_metadata() -> None:
    """Fill in metadata for movies lacking it using TMDb."""
    slog = StepLogger("step_6_enrich_metadata")
    movies = get_movies_missing_metadata()
    slog.set_input_count(len(movies))
    slog.logger.info("Enriching metadata for %s movies", len(movies))

    tasks = [_enrich_movie(movie, slog) for movie in movies]
    await asyncio.gather(*tasks, return_exceptions=True)
    slog.logger.info("Metadata enrichment complete")
    slog.finalize()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(enrich_metadata())