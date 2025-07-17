"""
Orchestrator for Step 3: Classify parsed reviews as film reviews using multiple LLM models and reconcile the results.

This script fetches parsed pages, dispatches each to configured LLMs in parallel,
reconciles the classifications, and stores the final result.
"""

import asyncio
import json
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List
from aiolimiter import AsyncLimiter

from crawler.db.scraper_queries import get_unpromoted_pages
from crawler.db.llm_log_queries import generate_task_fingerprint, batch_insert_llm_logs
from crawler.llm.llm_controller_pydantic import LLMControllerPydantic
from crawler.llm.reconcile import reconcile_classifications
from crawler.llm.schemas import LLMClassificationOutput
from crawler.llm.prompts.page_classification_system_prompt import PAGE_CLASSIFICATION_SYSTEM_PROMPT_TEMPLATE
from crawler.llm.prompts.page_classification_user_prompt import PAGE_CLASSIFICATION_USER_PROMPT_TEMPLATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLASSIFICATION_MODELS = [
    "gemma2-9b-it",
    "claude-3-5-haiku-latest"
]
PRIORITY_MODEL = "gemini-1.5-pro"

async def classify_reviews_pydantic():
    """
    Main function to fetch parsed reviews, classify them using multiple LLMs,
    reconcile the results, and log the final outcome.
    """
    logger.info("Starting LLM classification and reconciliation of parsed pages...")
    load_dotenv()
    llm_controller = LLMControllerPydantic()

    parsed_pages = get_unpromoted_pages()
    if not parsed_pages:
        logger.info("No parsed pages found to classify.")
        return

    logger.info(f"Found {len(parsed_pages)} parsed pages to classify.")
    limiter = AsyncLimiter(1, 5)  # Rate limiter: 1 request every 5 seconds

    tasks = [
        process_page_classification(limiter, llm_controller, page, i, len(parsed_pages))
        for i, page in enumerate(parsed_pages, 1)
    ]

    await asyncio.gather(*tasks)
    logger.info("Finished LLM classification and reconciliation of parsed reviews.")

async def process_page_classification(limiter: AsyncLimiter, llm_controller: LLMControllerPydantic, page_data: Dict[str, Any], page_num: int, total_pages: int):
    """
    Orchestrates the classification of a single page by multiple models,
    runs reconciliation, and logs the final result.
    """
    logger.info(f"Processing page {page_num}/{total_pages} (ID: {page_data['id']})...")

    classification_tasks = [
        classify_review_with_llm(limiter, llm_controller, model, page_data)
        for model in CLASSIFICATION_MODELS
    ]

    model_outputs = await asyncio.gather(*classification_tasks)

    # Filter out any None results from failed classifications
    valid_outputs = [output for output in model_outputs if output]

    reconciliation_result = reconcile_classifications(valid_outputs, priority_model=PRIORITY_MODEL)

    _log_reconciliation_result(page_data, reconciliation_result, page_num, total_pages)

async def classify_review_with_llm(limiter: AsyncLimiter, llm_controller: LLMControllerPydantic, model_name: str, review_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs LLM classification for a single review and returns the result.
    """
    async with limiter:
        input_data = {
            "blog_title": review_data.get("parsed_title"),
            "short_review": review_data.get("parsed_short_review"),
            "full_review": review_data.get("full_review_truncated"),
        }

        system_prompt = PAGE_CLASSIFICATION_SYSTEM_PROMPT_TEMPLATE
        user_prompt = PAGE_CLASSIFICATION_USER_PROMPT_TEMPLATE.format(**input_data)

        try:
            output_pydantic = await llm_controller.prompt_llm(
                model_name,
                system_prompt,
                user_prompt,
                response_model=LLMClassificationOutput
            )
            return {
                "model": model_name,
                "classification": output_pydantic.is_film_review,
                "confidence": None,  # Confidence is not provided by the models
                "details": output_pydantic.model_dump()
            }
        except Exception as e:
            logger.error(f"Failed to get valid classification from {model_name}: {e}")
            return None

def _log_reconciliation_result(review_data: Dict[str, Any], result: Dict[str, Any], page_num: int, total_pages: int):
    """
    Logs the final, reconciled classification result to the database.
    """
    task_fingerprint = generate_task_fingerprint("classify_page", review_data["id"])

    log_row = {
        "source_table": "raw_scraped_pages",
        "source_id": review_data["id"],
        "model_name": "reconciliation",
        "task_type": "classify_page",
        "input_data": {"strategy": result.get("strategy"), "contributing_models": result.get("contributing_models")},
        "task_fingerprint": task_fingerprint,
        "output_raw": json.dumps(result),
        "is_movie_review": result.get("final_classification"),
        "sentiment": None,  # This would need a reconciliation strategy too
        "movie_name": None, # This would need a reconciliation strategy too
        "accepted": result.get("final_classification") != "failed",
    }

    try:
        batch_insert_llm_logs([log_row])
        logger.info(f"Inserted reconciled log for page {page_num}/{total_pages} (ID: {review_data['id']}) -> {result.get('final_classification')}")
    except Exception as e:
        logger.error(f"Failed to insert reconciled log for source_id {review_data['id']}: {e}")

if __name__ == "__main__":
    asyncio.run(classify_reviews_pydantic())
