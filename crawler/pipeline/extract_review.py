"""Unified review processing pipeline - EXTRACT stage."""
import asyncio
import importlib
import json
import logging
from typing import Optional

from crawler.llm.client import process_with_llm
from crawler.llm.schemas import ProcessedReview
from crawler.db.scraper_queries import get_parsed_pages, batch_update_status, update_page_extract_results, update_page_extraction_failed

logger = logging.getLogger(__name__)


async def process_single_review(
    page: dict,
    model: str,
    prompt_module,
) -> tuple[str, Optional[ProcessedReview], Optional[str]]:
    """
    Process a single review through the LLM.

    Returns:
        Tuple of (page_id, result, error)
    """
    page_id = page["id"]

    try:
        user_prompt = prompt_module.USER_PROMPT_TEMPLATE.format(
            title=page.get("parsed_title", "") or "",
            summary=page.get("parsed_short_review", "") or "",
            full_review=page.get("parsed_full_review", "") or "",
        )

        result = await process_with_llm(
            model=model,
            system_prompt=prompt_module.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=ProcessedReview,
        )

        logger.info(f"Processed {page_id}: is_film_review={result.is_film_review}, movies={result.movie_names}")
        return page_id, result, None

    except Exception as e:
        logger.error(f"Failed to process {page_id}: {e}")
        return page_id, None, str(e)


async def run_extract_pipeline(
    model: str = "anthropic/claude-sonnet-4-20250514",
    prompt_version: str = "v1",
    limit: int = 10,
    dry_run: bool = False,
    concurrency: int = 5,
) -> dict:
    """
    Run the EXTRACT stage - process reviews with single LLM call.

    Args:
        model: LLM to use (e.g., "anthropic/claude-3-5-sonnet-latest")
        prompt_version: Prompt version to use (e.g., "v1")
        limit: Maximum reviews to process
        dry_run: If True, don't write to database
        concurrency: Max concurrent LLM calls

    Returns:
        Summary dict with counts and errors
    """
    # Load prompt module
    prompt_module = importlib.import_module(
        f"crawler.llm.prompts.process_review_{prompt_version}"
    )
    logger.info(f"Using prompt {prompt_version}: {prompt_module.DESCRIPTION}")

    # Fetch parsed pages ready for EXTRACT
    pages = get_parsed_pages(limit=limit)
    logger.info(f"Fetched {len(pages)} pages to process")

    if not pages:
        return {"processed": 0, "film_reviews": 0, "non_reviews": 0, "errors": 0}

    # Process with controlled concurrency
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_semaphore(page):
        async with semaphore:
            return await process_single_review(page, model, prompt_module)

    results = await asyncio.gather(*[
        process_with_semaphore(page) for page in pages
    ])

    # Aggregate results
    processed = 0
    film_reviews = []
    non_reviews = []
    errors = []

    for page_id, result, error in results:
        if error:
            errors.append({"page_id": page_id, "error": error})
            # Mark as extraction_failed in DB
            if not dry_run:
                update_page_extraction_failed(page_id, error, model_name=model)
            continue

        processed += 1

        if result.is_film_review:
            film_reviews.append({
                "page_id": page_id,
                "cleaned_title": result.cleaned_title,
                "cleaned_short_review": result.cleaned_short_review,
                "movie_names": result.movie_names,
                "sentiment": result.sentiment,
            })
        else:
            non_reviews.append(page_id)

    # Write to database
    if not dry_run:
        if film_reviews:
            # Update pages table with extraction results
            for review in film_reviews:
                movie_names_json = json.dumps(review["movie_names"]) if isinstance(review["movie_names"], list) else review["movie_names"]
                update_page_extract_results(
                    page_id=review["page_id"],
                    is_film_review=True,
                    movie_names=movie_names_json,
                    sentiment=review["sentiment"],
                    cleaned_title=review["cleaned_title"],
                    cleaned_short_review=review["cleaned_short_review"],
                    model_name=model
                )
            logger.info(f"Updated {len(film_reviews)} pages with extraction results")

        if non_reviews:
            batch_update_status(non_reviews, "not_extracted")
            logger.info(f"Marked {len(non_reviews)} as not_extracted")

    summary = {
        "processed": processed,
        "film_reviews": len(film_reviews),
        "non_reviews": len(non_reviews),
        "errors": len(errors),
        "error_details": errors if errors else None,
        "model": model,
        "prompt_version": prompt_version,
    }

    logger.info(f"Extract pipeline complete: {summary}")
    return summary
