"""Orchestrate the weekly enrichment pipeline."""
import argparse
import asyncio
from pipeline import (
    step_1_fetch_links,
    step_2_parse_posts,
    step_3_classify_reviews,
    step_3b_llm_validation,
    step_4_link_movies,
    step_5_generate_sentiment,
    step_6_enrich_metadata,
)
from utils.logger import get_logger

logger = get_logger(__name__)

async def crawl(limit: int | None = None, dry_run: bool = False, reviewer: str = "baradwajrangan") -> list[str]:
    logger.info("Starting crawl stage")
    links = await step_1_fetch_links.fetch_links(reviewer=reviewer)
    if limit:
        links = links[:limit]
        logger.debug("Limiting to %s links", limit)

    if dry_run:
        logger.info("Dry run enabled - exiting early")
        return []

    await step_2_parse_posts.parse_posts(links, reviewer=reviewer)
    logger.info("Crawl stage complete")
    return links


def validate() -> None:
    logger.info("Starting validation stage")
    step_3_classify_reviews.classify_reviews()
    step_3b_llm_validation.validate_reviews()
    step_4_link_movies.link_movies()
    logger.info("Validation stage complete")


async def enrich() -> None:
    logger.info("Starting enrichment stage")
    step_5_generate_sentiment.generate_sentiment()
    await step_6_enrich_metadata.enrich_metadata()
    logger.info("Enrichment stage complete")


async def main(limit: int | None = None, dry_run: bool = False, reviewer: str = "baradwajrangan") -> None:
    await crawl(limit=limit, dry_run=dry_run, reviewer=reviewer)
    if dry_run:
        return
    validate()
    await enrich()
    logger.info("Pipeline run complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run enrichment pipeline")
    parser.add_argument("--limit", type=int, help="Limit number of links to process")
    parser.add_argument("--dry-run", action="store_true", help="Run fetch step only")
    parser.add_argument("--reviewer", default="baradwajrangan", help="Reviewer id to crawl")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, dry_run=args.dry_run, reviewer=args.reviewer))
