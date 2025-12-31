"""ENRICH stage: use TMDb to enrich movie metadata."""
import asyncio
from review_aggregator.db.movie_queries import get_movies_pending_enrichment, update_movie_metadata, update_movie_status
from review_aggregator.db.review_queries import get_post_date_for_movie
from review_aggregator.tmdb.tmdb_api import search_tmdb
from review_aggregator.utils.io_helpers import write_failure
from review_aggregator.utils import StepLogger

CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _enrich_movie(movie: dict, step_logger: StepLogger) -> None:
    try:
        async with semaphore:
            metadata = await search_tmdb(movie["title"], movie.get("review_year"))
        if metadata:
            update_movie_metadata(movie["id"], metadata, source="tmdb")
            update_movie_status(movie["id"], "enriched")
            step_logger.metrics["saved_count"] += 1
            step_logger.logger.info("Updated metadata for %s", movie["title"])
        else:
            # No TMDB match found - mark as failed
            update_movie_status(movie["id"], "enrichment_failed", "No TMDB match found")
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.warning("No metadata found for %s", movie["title"])
    except Exception as e:
        update_movie_status(movie["id"], "enrichment_failed", str(e))
        step_logger.metrics["failed_count"] += 1
        step_logger.logger.error(
            "TMDb enrichment failed for %s: %s", movie.get("title"), e
        )
        write_failure("failed_tmdb.txt", movie.get("title", ""), e)


async def enrich_metadata() -> None:
    """Fill in metadata for movies with status='pending_enrichment' using TMDb."""
    step_logger = StepLogger("enrich_metadata")
    movies = get_movies_pending_enrichment()
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
