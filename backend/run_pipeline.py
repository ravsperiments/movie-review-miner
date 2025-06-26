"""Orchestrate the weekly enrichment pipeline."""
import asyncio
from pipeline import (
    step_1_fetch_links,
    step_2_parse_posts,
    step_3_classify_reviews,
    step_4_link_movies,
    step_5_generate_sentiment,
    step_6_enrich_metadata,
)
from utils.logger import get_logger

logger = get_logger(__name__)

async def main() -> None:
    logger.info("Starting pipeline run")
    links = await step_1_fetch_links.fetch_links()
    await step_2_parse_posts.parse_posts(links)
    step_3_classify_reviews.classify_reviews()
    step_4_link_movies.link_movies()
    step_5_generate_sentiment.generate_sentiment()
    await step_6_enrich_metadata.enrich_metadata()
    logger.info("Pipeline run complete")

if __name__ == "__main__":
    asyncio.run(main())
