#!/usr/bin/env python3
"""
Movie Review Miner - Pipeline CLI

Pipeline Stages:
    1. CRAWL   - Fetch links + Parse pages (no LLM)
    2. EXTRACT - Single LLM call: classify + clean + sentiment
    3. ENRICH  - Add TMDB metadata

Modes:
    prod  - Uses local.db (default, production data)
    test  - Uses test.db (isolated test database)
    eval  - Runs golden set evaluation

Usage:
    # Run full pipeline (prod mode)
    python run_pipeline.py --stage all

    # Run specific stages
    python run_pipeline.py --stage crawl
    python run_pipeline.py --stage extract --model anthropic/claude-3-5-sonnet-latest --prompt v1
    python run_pipeline.py --stage enrich

    # Test mode (uses test.db)
    python run_pipeline.py --mode test --stage crawl
    python run_pipeline.py --mode test --stage extract

    # Run evaluation
    python run_pipeline.py --mode eval --model anthropic/claude-3-5-sonnet-latest --prompt v1

    # Dry run (no DB writes)
    python run_pipeline.py --stage extract --dry-run --limit 5
"""
import argparse
import asyncio
import logging
from pathlib import Path

from crawler.utils.logger import get_logger, setup_pipeline_logging

logger = get_logger(__name__)

# Database paths for different modes
CRAWLER_DIR = Path(__file__).parent
DB_PATHS = {
    "prod": CRAWLER_DIR / "local.db",
    "test": CRAWLER_DIR / "test.db",
}


def setup_database(mode: str) -> None:
    """Configure database path based on mode."""
    if mode == "eval":
        # Eval mode doesn't use the DB
        return

    from crawler.db.sqlite_client import set_db_path

    db_path = DB_PATHS.get(mode, DB_PATHS["prod"])
    set_db_path(db_path)
    logger.info(f"Using database: {db_path}")


async def crawl(limit: int | None = None, dry_run: bool = False) -> list[str]:
    """Stage 1: CRAWL - Fetch links and parse pages."""
    from crawler.pipeline.crawl_fetch_links import orchestrate_fetch_links
    from crawler.pipeline.crawl_posts import parse_posts
    from crawler.db.scraper_queries import get_pending_pages_to_parse

    logger.info("Starting CRAWL stage")

    # Step 1: Fetch links
    await orchestrate_fetch_links()

    if dry_run:
        logger.info("Dry run - skipping parse")
        return []

    # Step 2: Parse posts
    pages = get_pending_pages_to_parse()
    if limit:
        pages = pages[:limit]

    if pages:
        await parse_posts(pages)

    logger.info(f"CRAWL complete - processed {len(pages) if pages else 0} links")
    return [p['page_url'] for p in pages] if pages else []


async def extract(
    model: str = "anthropic/claude-sonnet-4-20250514",
    prompt_version: str = "v1",
    limit: int = 10,
    dry_run: bool = False,
    concurrency: int = 5,
) -> dict:
    """Stage 2: EXTRACT - Process reviews with single LLM call."""
    from crawler.pipeline.extract_review import run_extract_pipeline

    logger.info(f"Starting EXTRACT stage: model={model}, prompt={prompt_version}")

    result = await run_extract_pipeline(
        model=model,
        prompt_version=prompt_version,
        limit=limit,
        dry_run=dry_run,
        concurrency=concurrency,
    )

    logger.info(f"EXTRACT complete: {result['film_reviews']} reviews, {result['non_reviews']} non-reviews")
    return result


async def enrich() -> None:
    """Stage 3: ENRICH - Add TMDB metadata."""
    from crawler.pipeline import enrich_movie_data

    logger.info("Starting ENRICH stage")

    if hasattr(enrich_movie_data, 'enrich_metadata'):
        await enrich_movie_data.enrich_metadata()

    logger.info("ENRICH complete")


async def run_eval(
    model: str,
    prompt_version: str,
    concurrency: int = 3,
) -> dict:
    """Run evaluation against golden set."""
    from crawler.eval.runner import run_evaluation

    logger.info(f"Starting evaluation: model={model}, prompt={prompt_version}")

    result = await run_evaluation(
        model=model,
        prompt_version=prompt_version,
        concurrency=concurrency,
    )

    return result


async def main(args) -> None:
    """Run the movie review mining pipeline."""
    setup_pipeline_logging()

    # Configure database based on mode (must be done before any DB imports)
    setup_database(args.mode)

    if args.mode == "eval":
        # Evaluation mode
        result = await run_eval(
            model=args.model,
            prompt_version=args.prompt,
            concurrency=args.concurrency,
        )

        print(f"\n{'='*50}")
        print("EVALUATION SUMMARY")
        print(f"{'='*50}")
        print(f"Model:    {result['meta']['model']}")
        print(f"Prompt:   {result['meta']['prompt_version']}")
        print(f"Accuracy: {result['summary']['accuracy']:.1%}")
        print(f"Passed:   {result['summary']['passed']}/{result['meta']['total_cases']}")
        print(f"\nField Accuracy:")
        for field, acc in result['summary']['field_accuracy'].items():
            print(f"  {field}: {acc:.1%}")

        if result['failures']:
            print(f"\nFailures ({len(result['failures'])}):")
            for f in result['failures'][:5]:
                failed_fields = list(f.get('field_results', {}).keys()) if f.get('field_results') else []
                print(f"  - {f['test_id']}: {f.get('error') or failed_fields}")

        return

    # Pipeline mode
    try:
        if args.stage in ["all", "crawl"]:
            await crawl(limit=args.limit, dry_run=args.dry_run)

        if args.dry_run and args.stage == "crawl":
            logger.info("Dry run complete")
            return

        if args.stage in ["all", "extract"]:
            result = await extract(
                model=args.model,
                prompt_version=args.prompt,
                limit=args.limit,
                dry_run=args.dry_run,
                concurrency=args.concurrency,
            )

            print(f"\n{'='*50}")
            print("EXTRACT SUMMARY")
            print(f"{'='*50}")
            print(f"Processed:    {result['processed']}")
            print(f"Film Reviews: {result['film_reviews']}")
            print(f"Non-Reviews:  {result['non_reviews']}")
            print(f"Errors:       {result['errors']}")

        if args.stage in ["all", "enrich"]:
            await enrich()

        logger.info("Pipeline complete")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Movie Review Miner Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py --stage extract --limit 10
  python run_pipeline.py --stage extract --model groq/llama-3.1-70b-versatile
  python run_pipeline.py --mode eval --model anthropic/claude-3-5-sonnet-latest --prompt v1
        """
    )

    parser.add_argument(
        "--mode",
        choices=["prod", "test", "eval"],
        default="prod",
        help="Run mode: 'prod' uses local.db, 'test' uses test.db, 'eval' for golden set testing"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "crawl", "extract", "enrich"],
        default="all",
        help="Pipeline stage to run (default: all)"
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-sonnet-4-20250514",
        help="LLM to use (e.g., anthropic/claude-sonnet-4-20250514, groq/llama-3.1-70b-versatile)"
    )
    parser.add_argument(
        "--prompt",
        default="v1",
        help="Prompt version (e.g., v1, v2)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max reviews to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write to database"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent LLM calls"
    )

    args = parser.parse_args()
    asyncio.run(main(args))
