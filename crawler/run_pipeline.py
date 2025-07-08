"""Orchestrate the weekly enrichment pipeline."""
import argparse
import asyncio
from crawler.pipeline import (
    crawl_step2_parse_posts,
    val_step1_classify_reviews,
    val_step2_llm_validation,
    val_step3_link_movies,
    enrich_step1_generate_sentiment,
    enrich_step2_add_metadata,
)
from crawler.pipeline.fetch_links_orchestrator import orchestrate_fetch_links
from crawler.utils.logger import get_logger
from crawler.llm import set_llm_model

logger = get_logger(__name__)

async def crawl(limit: int | None = None, dry_run: bool = False) -> list[str]:
    logger.info("Starting crawl stage")
    await orchestrate_fetch_links()
    # The orchestrator handles storing links, so we don't need to return them here for now.
    # If subsequent steps need the links, they should query the database.
    links = [] # Placeholder for now, as links are stored directly by orchestrator
    if limit:
        links = links[:limit]
        logger.debug("Limiting to %s links", limit)

    if dry_run:
        logger.info("Dry run enabled - exiting early")
        return []

    await crawl_step2_parse_posts.parse_posts(links)
    logger.info("Crawl stage complete")
    return links


def validate() -> None:
    logger.info("Starting validation stage")
    val_step1_classify_reviews.classify_reviews()
    val_step2_llm_validation.validate_reviews()
    val_step3_link_movies.link_movies()
    logger.info("Validation stage complete")


async def enrich() -> None:
    logger.info("Starting enrichment stage")
    enrich_step1_generate_sentiment.generate_sentiment()
    await enrich_step2_add_metadata.enrich_metadata()
    logger.info("Enrichment stage complete")


async def main(limit: int | None = None, dry_run: bool = False) -> None:
    await crawl(limit=limit, dry_run=dry_run)
    if dry_run:
        return
    validate()
    await enrich()
    logger.info("Pipeline run complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run enrichment pipeline")
    parser.add_argument("--limit", type=int, help="Limit number of links to process")
    parser.add_argument("--dry-run", action="store_true", help="Run fetch step only")
    
    parser.add_argument(
        "--llm-model",
        default=None,
        choices=["openai", "llama"],
        help="LLM model to use (overrides LLM_MODEL env)",
    )
    args = parser.parse_args()

    if args.llm_model:
        set_llm_model(args.llm_model)

    asyncio.run(main(limit=args.limit, dry_run=args.dry_run))
