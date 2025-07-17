"""
Orchestrator for Step 3: classify parsed reviews as film reviews using multiple LLM models.

This script fetches parsed pages, dispatches each to the configured LLMs in parallel,
and batches the results into the staging table (stg_llm_logs) for later processing.
"""

import asyncio
import json
import re
import logging
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Union
from aiolimiter import AsyncLimiter

from crawler.db.scraper_queries import get_unpromoted_pages
from crawler.db.llm_log_queries import generate_task_fingerprint, batch_insert_llm_logs
from crawler.llm.llm_controller import LLMController
from crawler.llm.prompts.page_classification_system_prompt import PAGE_CLASSIFICATION_SYSTEM_PROMPT_TEMPLATE
from crawler.llm.prompts.page_classification_user_prompt import PAGE_CLASSIFICATION_USER_PROMPT_TEMPLATE
from crawler.llm.reconcile_llm_output.reconcile_review_classification import run_reconciliation_pipeline


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map each classification task type to the JSON field to extract
EXTRACT_FIELD_FOR_TASK: Dict[str, List[str]] = {
    "classify_page": ["is_film_review", "film_names", "sentiment"],
}

CLASSIFICATION_MODELS = {
    "primary": "gemma2-9b-it",
    "judge": "claude-3-5-sonnet",
}


async def classify_reviews():
    """
    Main function to fetch parsed reviews, classify them using multiple LLMs in parallel,
    and log the results.
    """
    logger.info("Starting LLM classification of parsed pages...")
    load_dotenv()  # Load environment variables
    llm_controller = LLMController()

    parsed_pages = get_unpromoted_pages()
    if not parsed_pages:
        logger.info("No parsed pages found to classify.")
        #return

    logger.info(f"Found {len(parsed_pages)} parsed pages to classify.")

    # Rate limiter: 40 requests per 60 seconds
    limiter = AsyncLimiter(1, 5)

    tasks = []
    total_pages = len(parsed_pages)

    for counter, page in enumerate(parsed_pages, start=1):
        for model_name in CLASSIFICATION_MODELS.values():
            tasks.append(
                classify_review_with_llm(
                    limiter, llm_controller, model_name, page, counter, total_pages
                )
            )

    await asyncio.gather(*tasks)
    logger.info("Finished LLM classification of parsed reviews.")

    # After classification, run the reconciliation process
    logger.info("Starting LLM output reconciliation...")
    run_reconciliation_pipeline(
        primary_model=CLASSIFICATION_MODELS["primary"],
        judge_model=CLASSIFICATION_MODELS["judge"],
    )
    logger.info("Finished LLM output reconciliation.")


async def classify_review_with_llm(
    limiter: AsyncLimiter,
    llm_controller: LLMController,
    model_name: str,
    review_data: Dict[str, Any],
    page_num: int,
    total_pages: int,
) -> None:
    """
    Performs LLM classification for a single review and inserts the result if valid.
    """
    async with limiter:
        task_type = "classify_page"
        input_data = {
            "blog_title": review_data.get("parsed_title"),
            "short_review": review_data.get("parsed_short_review"),
            "full_review": review_data.get("full_review_truncated"),
        }

        system_prompt = PAGE_CLASSIFICATION_SYSTEM_PROMPT_TEMPLATE
        user_prompt = PAGE_CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
            blog_title=input_data["blog_title"],
            short_review=input_data["short_review"],
            full_review=input_data["full_review"],
        )

        output_raw = await llm_controller.prompt_llm(
            model_name, system_prompt, user_prompt
        ) or ""
        output_parsed = _parse_llm_output(output_raw, task_type)
        _log_llm_result(
            review_data, model_name, task_type, input_data, output_raw, output_parsed, page_num, total_pages
        )


def _parse_llm_output(output_raw: str, task_type: str) -> Union[str, Dict[str, Any]]:
    """
    Parses and cleans the JSON output from the LLM.
    """
    try:
        # Remove markdown fences around JSON if present
        fenced = re.match(
            r"```(?:json)?\s*(.*)\s*```$", output_raw.strip(), flags=re.DOTALL
        )
        cleaned = fenced.group(1).strip() if fenced else output_raw.strip()

        # Fix unquoted values like: is_film_review: Maybe
        cleaned = re.sub(
            r'"is_film_review":\s*(Yes|No|Maybe)', r'"is_film_review": "\1"', cleaned
        )

        output_parsed = json.loads(cleaned)
        # Extract only the single field we care about based on task_type
        if isinstance(output_parsed, dict):
            fields = EXTRACT_FIELD_FOR_TASK.get(task_type)
            extracted_values = {}
            if fields:
                for field in fields:
                    if field in output_parsed:
                        extracted_values[field] = output_parsed[field]
                        # Normalize booleans/strings for film-review task
                logger.info(f"extraced value: {extracted_values}")
                return extracted_values
        return output_parsed
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
        return {"error": "JSON_DECODE_ERROR", "raw_output": output_raw}
    except Exception as e:
        logger.error(f"Failed to parse LLM output: {e}")
        return {"error": str(e), "raw_output": output_raw}


def _log_llm_result(
    review_data: Dict[str, Any],
    model_name: str,
    task_type: str,
    input_data: Dict[str, Any],
    output_raw: str,
    output_parsed: Union[str, Dict[str, Any]],
    page_num: int,
    total_pages: int,
) -> None:
    """
    Logs the LLM result to the database.
    """
    task_fingerprint = generate_task_fingerprint(task_type, review_data["id"])
    model_clean = re.sub(r"[^A-Za-z0-9_.-]", "", model_name)
    log_row = {
        "source_table": "raw_scraped_pages",
        "source_id": review_data["id"],
        "model_name": model_clean,
        "task_type": task_type,
        "input_data": input_data,
        "task_fingerprint": task_fingerprint,
        "output_raw": output_raw,
        "is_movie_review": None,
        "sentiment": None,
        "movie_name": None,
        "accepted": False,
    }
    if isinstance(output_parsed, dict) and "error" not in output_parsed:
        log_row["accepted"] = True
        log_row["is_movie_review"] = output_parsed.get("is_film_review")
        log_row["sentiment"] = output_parsed.get("sentiment")
        log_row["movie_name"] = output_parsed.get("film_names")

    if log_row["accepted"]:
        try:
            batch_insert_llm_logs([log_row])
            logger.info(
                f"Inserted LLM log for page num {page_num} of {total_pages} | source_id {review_data['id']}, model {model_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to insert LLM log for source_id {review_data['id']} | model {model_name}: {e}"
            )


if __name__ == "__main__":
    asyncio.run(classify_reviews())
