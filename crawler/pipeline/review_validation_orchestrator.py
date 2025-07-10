"""
Orchestrator for Step 3: classify parsed reviews as film reviews using multiple LLM models.

This script fetches parsed pages, dispatches each to the configured LLMs in parallel,
and batches the results into the staging table (stg_llm_logs) for later processing.
"""

import asyncio
import json
import re
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List
from aiolimiter import AsyncLimiter

from crawler.db.scraper_queries import get_unpromoted_pages
from crawler.db.llm_log_queries import generate_task_fingerprint, batch_insert_llm_logs
from crawler.llm.llm_controller import LLMController
from crawler.llm.prompts.is_film_review_prompt import IS_FILM_REVIEW_PROMPT_TEMPLATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map each classification task type to the JSON field to extract
EXTRACT_FIELD_FOR_TASK: Dict[str, str] = {
    "is_film_review": "is_film_review",
}

async def classify_review_with_llm(limiter: AsyncLimiter, llm_controller: LLMController, model_name: str, review_data: Dict[str, Any]) -> None:
    """
    Performs LLM classification for a single review and inserts the result if valid.
    """
    async with limiter:
        # Define the classification task and assemble the input fields
        task_type = "is_film_review"
    input_data = {
        "blog_title": review_data.get("parsed_title"),
        "short_review": review_data.get("parsed_short_review"),
        "full_review": review_data.get("parsed_full_review"),
    }

    prompt = IS_FILM_REVIEW_PROMPT_TEMPLATE.format(
        blog_title=input_data['blog_title'],
        short_review=input_data['short_review'],
        full_review=input_data['full_review']
    )

    # Call the LLM and parse the JSON output (strip code fences if needed)
    output_raw = ""
    output_parsed = {}
    try:
        response = await llm_controller.prompt_llm(model_name, prompt)
        output_raw = response or ""
        # Remove markdown fences around JSON if present
        fenced = re.match(r"```(?:json)?\s*(.*)\s*```$", output_raw.strip(), flags=re.DOTALL)
        cleaned = fenced.group(1).strip() if fenced else output_raw.strip()

        # Fix unquoted values like: is_film_review: Maybe
        # (avoid lookbehind; match the whole expression instead)
        cleaned = re.sub(r'"is_film_review":\s*(Yes|No|Maybe)', r'"is_film_review": "\1"', cleaned)

        output_parsed = json.loads(cleaned)
        # Extract only the single field we care about based on task_type
        if isinstance(output_parsed, dict):
            field = EXTRACT_FIELD_FOR_TASK.get(task_type)
            if field and field in output_parsed:
                value = output_parsed[field]
                # Normalize booleans/strings for film-review task
                if isinstance(value, bool):
                    value = "yes" if value else "no"
                elif isinstance(value, str) and task_type == "is_film_review":
                    val_lower = value.strip().lower()
                    value = val_lower if val_lower in ("yes", "no", "maybe") else "maybe"
                output_parsed = value
        logger.info("Model %s for source_id %s returned parsed JSON", model_name, review_data['id'])
    except json.JSONDecodeError as e:
        logger.error("JSON decoding error (model %s, source_id %s): %s", model_name, review_data['id'], e)
        output_parsed = {"error": "JSON_DECODE_ERROR", "raw_output": output_raw}
    except Exception as e:
        logger.error("Classification failed (model %s, source_id %s): %s", model_name, review_data['id'], e)
        output_parsed = {"error": str(e), "raw_output": output_raw}

    task_fingerprint = generate_task_fingerprint(task_type, review_data["id"])

    # Prepare log row for this model and insert it immediately to avoid data loss
    log_row = {
        "source_table": "raw_scraped_pages",
        "source_id": review_data["id"],
        # Sanitize model_name for DB: keep only alphanumeric, underscore, and hyphen
        "model_name": re.sub(r"[^A-Za-z0-9_.-]", "", model_name),
        "task_type": task_type,
        "input_data": input_data,
        "task_fingerprint": task_fingerprint,
        "output_raw": output_raw,
        "output_parsed": output_parsed,
        "accepted": not (isinstance(output_parsed, dict) and "error" in output_parsed),
    }
    if log_row["accepted"]:
        try:
            batch_insert_llm_logs([log_row])
            logger.info("Inserted LLM log for source_id %s, model %s", review_data['id'], model_name)
        except Exception as e:
            logger.error("Failed to insert LLM log for source_id %s, model %s: %s", review_data['id'], model_name, e)

CLASSIFICATION_MODELS = [
    "grok-3-mini-fast",
]

async def classify_reviews():
    """
    Main function to fetch parsed reviews, classify them using multiple LLMs in parallel,
    and log the results.
    """
    logger.info("Starting LLM classification of parsed reviews...")
    load_dotenv() # Load environment variables
    llm_controller = LLMController()

    parsed_pages = get_unpromoted_pages()
    if not parsed_pages:
        logger.info("No parsed pages found to classify.")
        return

    logger.info(f"Found {len(parsed_pages)} parsed pages to classify.")

    # Rate limiter: 5 requests per second
    limiter = AsyncLimiter(2, 1)

    tasks: List[asyncio.Task] = []
    for page in parsed_pages:
        # Run classification with each configured model in parallel
        for model_name in CLASSIFICATION_MODELS:
            task = asyncio.create_task(classify_review_with_llm(limiter, llm_controller, model_name, page))
            tasks.append(task)

    await asyncio.gather(*tasks)
    logger.info(f"All classification tasks finished")
    logger.info("Finished LLM classification of parsed reviews.")

if __name__ == "__main__":
    asyncio.run(classify_reviews())
