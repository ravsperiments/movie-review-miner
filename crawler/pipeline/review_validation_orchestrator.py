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
from typing import Dict, Any, List, Union
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

def _parse_llm_output(output_raw: str, task_type: str) -> Union[str, Dict[str, Any]]:
    """
    Parses and cleans the JSON output from the LLM.
    """
    try:
        # Remove markdown fences around JSON if present
        fenced = re.match(r"```(?:json)?\s*(.*)\s*```$", output_raw.strip(), flags=re.DOTALL)
        cleaned = fenced.group(1).strip() if fenced else output_raw.strip()

        # Fix unquoted values like: is_film_review: Maybe
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
                return value
        return output_parsed
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
        return {"error": "JSON_DECODE_ERROR", "raw_output": output_raw}
    except Exception as e:
        logger.error(f"Failed to parse LLM output: {e}")
        return {"error": str(e), "raw_output": output_raw}

def _log_llm_result(review_data: Dict[str, Any], model_name: str, task_type: str, input_data: Dict[str, Any], output_raw: str, output_parsed: Union[str, Dict[str, Any]]) -> None:
    """
    Logs the LLM result to the database.
    """
    task_fingerprint = generate_task_fingerprint(task_type, review_data["id"])

    log_row = {
        "source_table": "raw_scraped_pages",
        "source_id": review_data["id"],
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
            logger.info(f"Inserted LLM log for source_id {review_data['id']}, model {model_name}")
        except Exception as e:
            logger.error(f"Failed to insert LLM log for source_id {review_data['id']}, model {model_name}: {e}")

async def classify_review_with_llm(limiter: AsyncLimiter, llm_controller: LLMController, model_name: str, review_data: Dict[str, Any]) -> None:
    """
    Performs LLM classification for a single review and inserts the result if valid.
    """
    async with limiter:
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

        output_raw = await llm_controller.prompt_llm(model_name, prompt) or ""
        output_parsed = _parse_llm_output(output_raw, task_type)
        _log_llm_result(review_data, model_name, task_type, input_data, output_raw, output_parsed)

CLASSIFICATION_MODELS = [
    "gemma2-9b-it",
    "claude-3-5-haiku-latest",
    "claude-3-5-sonnet-latest",
    "grok-3-mini-fast",
    "gpt-4.1-nano",
    "gpt-4.1-mini",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite-preview-06-17",
    "phi3:mini"
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

    # Rate limiter: 40 requests per 60 seconds
    limiter = AsyncLimiter(1, 5)

    tasks = []
    for page in parsed_pages:
        for model_name in CLASSIFICATION_MODELS:
            tasks.append(classify_review_with_llm(limiter, llm_controller, model_name, page))

    await asyncio.gather(*tasks)
    logger.info("Finished LLM classification of parsed reviews.")

if __name__ == "__main__":
    asyncio.run(classify_reviews())
