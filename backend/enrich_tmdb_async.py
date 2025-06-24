import asyncio
from db.review_queries import (
    get_unenriched_links,
    update_review_with_movie_id,
)
from db.movie_queries import get_movie_by_title, create_movie, update_movie_metadata
from llm.openai_wrapper import extract_movie_title
from tmdb.tmdb_api import search_tmdb  # abstract your TMDb API call here
from utils.logger import get_logger

logger = get_logger(__name__)

async def enrich_reviews():
    reviews = get_unenriched_links()
    logger.info("Found %s reviews without movie linkage", len(reviews))

    for review in reviews:
        try:
            title = extract_movie_title(review["blog_title"])
            if not title:
                logger.warning("Skipping %s - no movie title extracted", review["id"])
                continue

            movie = get_movie_by_title(title)
            if movie:
                movie_id = movie["id"]
            else:
                movie_id = create_movie(title)

            update_review_with_movie_id(review["id"], movie_id)

            metadata = await search_tmdb(title)
            if metadata:
                update_movie_metadata(movie_id, metadata)

            logger.info("Enriched review %s with movie %s", review["id"], title)
        except Exception as e:
            logger.error("Failed to enrich review %s: %s", review.get("id", "?"), e)

if __name__ == "__main__":
    asyncio.run(enrich_reviews())
