"""
Orchestrator for cleaning parsed review fields using multiple LLM models.

This script fetches staged reviews, dispatches each to a primary LLM for cleaning,
then to a judge LLM for quality assessment, and logs the results to stg_llm_logs 
for later reconciliation.
"""

import asyncio
import json
import re
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Union
from aiolimiter import AsyncLimiter

from crawler.db.stg_clean_review_queries import get_staged_reviews
from crawler.db.llm_log_queries import generate_task_fingerprint, batch_insert_llm_logs
from crawler.llm.llm_controller import LLMController
from crawler.llm.prompts.clean_review_system_prompt import CLEAN_REVIEW_SYSTEM_PROMPT
from crawler.llm.prompts.judge_clean_review_system_prompt import JUDGE_CLEAN_REVIEW_SYSTEM_PROMPT
from crawler.llm.prompts.judge_clean_review_user_prompt import JUDGE_CLEAN_REVIEW_USER_PROMPT_TEMPLATE
from crawler.llm.reconcile_llm_output.reconcile_clean_review import run_clean_review_reconciliation_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map each cleaning task type to the JSON fields to extract
EXTRACT_FIELD_FOR_TASK: Dict[str, List[str]] = {
    "clean_review": ["cleaned_title", "cleaned_short_review"],
    "judge_review": ["is_title_valid", "is_short_review_valid"]
}

CLEAN_REVIEW_MODELS = {
    "primary": "claude-3-5-sonnet-latest",
    "judge": "claude-3-5-haiku-latest",
}


async def clean_reviews():
    """
    Main function to fetch staged reviews, clean them using multiple LLMs,
    and log the results for reconciliation.
    """
    logger.info("Starting LLM cleaning of staged reviews...")
    load_dotenv()
    llm_controller = LLMController()

    staged_reviews = get_staged_reviews(limit=5)
    if not staged_reviews:
        logger.info("No staged reviews found to clean.")
        return

    logger.info(f"Found {len(staged_reviews)} staged reviews to clean.")

    # Rate limiter: 1 request per 3 seconds to be conservative
    limiter = AsyncLimiter(1, 3)

    # First, run all primary cleaning tasks
    primary_tasks = []
    total_reviews = len(staged_reviews)

    for counter, review in enumerate(staged_reviews, start=1):
        primary_tasks.append(
            clean_review_with_llm(
                limiter, llm_controller, CLEAN_REVIEW_MODELS["primary"], 
                review, "clean_review", counter, total_reviews
            )
        )

    # Wait for all primary tasks to complete
    primary_results = await asyncio.gather(*primary_tasks, return_exceptions=True)
    
    # Now run judge tasks with access to cleaned content
    judge_tasks = []
    for counter, review in enumerate(staged_reviews, start=1):
        judge_tasks.append(
            judge_clean_review_with_llm(
                limiter, llm_controller, CLEAN_REVIEW_MODELS["judge"],
                review, "judge_review", counter, total_reviews
            )
        )

    await asyncio.gather(*judge_tasks, return_exceptions=True)
    logger.info("Finished LLM cleaning of staged reviews.")

    # After cleaning, run the reconciliation process
    logger.info("Starting clean review reconciliation...")
    run_clean_review_reconciliation_pipeline(
        primary_model=CLEAN_REVIEW_MODELS["primary"],
        judge_model=CLEAN_REVIEW_MODELS["judge"],
    )
    logger.info("Finished clean review reconciliation.")


async def clean_review_with_llm(
    limiter: AsyncLimiter,
    llm_controller: LLMController,
    model_name: str,
    review_data: Dict[str, Any],
    task_type: str,
    review_num: int,
    total_reviews: int,
) -> None:
    """
    Performs LLM cleaning for a single review and logs the result.
    """
    async with limiter:
        input_data = {
            "movie_name": review_data.get("movie_name"),
            "raw_title": review_data.get("raw_parsed_title"),
            "raw_short_review": review_data.get("raw_parsed_short_review"),
            "raw_full_review": review_data.get("raw_parsed_full_review"),
        }

        user_prompt = f"""
        Please clean the following movie review data for the film "{input_data["movie_name"]}":
        Title: {input_data["raw_title"]}
        Short Review: {input_data["raw_short_review"]}
        Full Review: {input_data["raw_full_review"]}
        """

        output_raw = await llm_controller.prompt_llm(
            model_name, CLEAN_REVIEW_SYSTEM_PROMPT, user_prompt
        ) or ""
        
        output_parsed = _parse_llm_output(output_raw, task_type)
        _log_llm_result(
            review_data, model_name, task_type, input_data, output_raw, output_parsed, 
            review_num, total_reviews
        )


async def judge_clean_review_with_llm(
    limiter: AsyncLimiter,
    llm_controller: LLMController,
    model_name: str,
    review_data: Dict[str, Any],
    task_type: str,
    review_num: int,
    total_reviews: int,
) -> None:
    """
    Performs quality assessment for cleaned review content and logs the result.
    """
    async with limiter:
        # Get the cleaned content from the most recent primary model output
        from crawler.db.llm_log_queries import get_latest_clean_review_output
        
        cleaned_content = get_latest_clean_review_output(
            review_data["raw_page_id"], 
            CLEAN_REVIEW_MODELS["primary"]
        )
        
        input_data = {
            "title_to_judge": cleaned_content.get("cleaned_title", ""),
            "short_review_to_judge": cleaned_content.get("cleaned_short_review", ""),
            "original_title": review_data.get("raw_parsed_title"),
            "original_short_review": review_data.get("raw_parsed_short_review"),
            "original_full_review": review_data.get("raw_parsed_full_review"),
        }

        user_prompt = JUDGE_CLEAN_REVIEW_USER_PROMPT_TEMPLATE.format(
            title_to_judge=input_data["title_to_judge"],
            short_review_to_judge=input_data["short_review_to_judge"],
            original_title=input_data["original_title"],
            original_short_review=input_data["original_short_review"],
            original_full_review=input_data["original_full_review"]
        )

        output_raw = await llm_controller.prompt_llm(
            model_name, JUDGE_CLEAN_REVIEW_SYSTEM_PROMPT, user_prompt
        ) or ""
        
        output_parsed = _parse_llm_output(output_raw, task_type)
        _log_llm_result(
            review_data, model_name, task_type, input_data, output_raw, output_parsed,
            review_num, total_reviews
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

        output_parsed = json.loads(cleaned)
        
        # Extract only the fields we care about based on task_type
        if isinstance(output_parsed, dict):
            fields = EXTRACT_FIELD_FOR_TASK.get(task_type)
            extracted_values = {}
            if fields:
                for field in fields:
                    if field in output_parsed:
                        extracted_values[field] = output_parsed[field]
                logger.info(f"Extracted values for {task_type}: {extracted_values}")
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
    review_num: int,
    total_reviews: int,
) -> None:
    """
    Logs the LLM result to the database.
    """
    task_fingerprint = generate_task_fingerprint(task_type, review_data["raw_page_id"])
    model_clean = re.sub(r"[^A-Za-z0-9_.-]", "", model_name)
    
    log_row = {
        "source_table": "vw_staged_reviews",
        "source_id": review_data["raw_page_id"],
        "model_name": model_clean,
        "task_type": task_type,
        "input_data": input_data,
        "task_fingerprint": task_fingerprint,
        "output_raw": output_raw,
        "cleaned_title": None,
        "cleaned_short_review": None,
        "is_title_valid": None,
        "is_short_review_valid": None,
        "accepted": False,
    }
    
    if isinstance(output_parsed, dict) and "error" not in output_parsed:
        log_row["accepted"] = True
        if task_type == "clean_review":
            log_row["cleaned_title"] = output_parsed.get("cleaned_title")
            log_row["cleaned_short_review"] = output_parsed.get("cleaned_short_review")
        elif task_type == "judge_review":
            log_row["is_title_valid"] = output_parsed.get("is_title_valid")
            log_row["is_short_review_valid"] = output_parsed.get("is_short_review_valid")

    if log_row["accepted"]:
        try:
            batch_insert_llm_logs([log_row])
            logger.info(
                f"Inserted LLM log for review {review_num} of {total_reviews} | "
                f"source_id {review_data['raw_page_id']}, model {model_name}, task {task_type}"
            )
        except Exception as e:
            logger.error(
                f"Failed to insert LLM log for source_id {review_data['raw_page_id']} | "
                f"model {model_name}, task {task_type}: {e}"
            )


if __name__ == "__main__":
    asyncio.run(clean_reviews())