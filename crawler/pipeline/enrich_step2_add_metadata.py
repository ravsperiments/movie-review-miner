"""Step 6: use TMDb to enrich movie metadata."""
import asyncio
from crawler.db.movie_queries import get_movies_missing_metadata, update_movie_metadata
from crawler.db.review_queries import get_post_date_for_movie
from crawler.tmdb.tmdb_api import search_tmdb
from crawler.utils.io_helpers import write_failure
from crawler.utils import StepLogger
from crawler.db.pipeline_logger import log_step_result
from tqdm import tqdm

CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _enrich_movie(movie: dict, step_logger: StepLogger) -> None:
    try:
        async with semaphore:
            metadata = await search_tmdb(movie["title"], movie["review_year"])
        if metadata:
            update_movie_metadata(movie["id"], metadata)
            step_logger.metrics["saved_count"] += 1
            step_logger.logger.info("Updated metadata for %s", movie["title"])
            log_step_result(
                "enrich_metadata",
                movie_id=movie.get("id"),
                attempt_number=1,
                status="success",
            )
        else:
            step_logger.logger.warning("No metadata found for %s", movie["title"])
            log_step_result(
                "enrich_metadata",
                movie_id=movie.get("id"),
                attempt_number=1,
                status="failure",
                error_message="No metadata",
            )
    except Exception as e:
        step_logger.metrics["failed_count"] += 1
        step_logger.logger.error(
            "TMDb enrichment failed for %s: %s", movie.get("title"), e, exc_info=True
        )
        write_failure("failed_tmdb.txt", movie.get("title", ""), e)
        log_step_result(
            "enrich_metadata",
            movie_id=movie.get("id"),
            attempt_number=1,
            status="failure",
            error_message=str(e),
        )


async def enrich_metadata() -> None:
    """Fill in metadata for movies lacking it using TMDb."""
    step_logger = StepLogger("step_6_enrich_metadata")
    movies = get_movies_missing_metadata()
    step_logger.metrics["input_count"] = len(movies)
    step_logger.logger.info("Enriching metadata for %s movies", len(movies))

    tasks = [_enrich_movie(movie, step_logger) for movie in movies]
    await asyncio.gather(*tasks, return_exceptions=True)
    step_logger.metrics["processed_count"] = step_logger.metrics["saved_count"] + step_logger.metrics["failed_count"]
    step_logger.logger.info("Metadata enrichment complete")
    step_logger.finalize()

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(enrich_metadata())
