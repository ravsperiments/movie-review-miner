"""
Orchestrates the parsing of raw blog post content and stores the extracted data in Supabase.

This script is responsible for:
1.  Fetching raw blog post entries that are marked as 'pending' or 'posted' from the database.
2.  Dynamically selecting the appropriate parsing logic based on the critic associated with each post.
3.  Executing the parsing process to extract structured data such as title, short description,
    full review content, and publication date.
4.  Updating the database with the parsed information, marking the post as 'parsed' upon success.
5.  Logging any errors encountered during the parsing process, updating the post's status to 'failed'
    and storing error details for debugging.
6.  Managing concurrency and retries for robust processing of multiple posts.
"""
import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm
from typing import Dict, Any

from crawler.scraper.parse_post import parse_post_async
from crawler.db.scraper_queries import get_pending_pages_to_parse, update_page_as_parsed, update_page_with_error
from crawler.utils.io_helpers import write_failure
from crawler.utils import StepLogger
from crawler.utils.retries import run_with_retries
from crawler.db.pipeline_logger import log_step_result
import json


# --- Configuration Constants ---
# Maximum number of concurrent HTTP requests to prevent overwhelming the source servers.
CONCURRENT_REQUESTS = 10
# Maximum number of retries for parsing a single post in case of transient errors.
MAX_RETRIES = 3
# Semaphore to control the number of concurrent asynchronous tasks.
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _parse_and_store(
    session: aiohttp.ClientSession,
    page: dict,
    step_logger: StepLogger,
    attempt: int = 1,
) -> None:
    """
    Parses a single blog post URL, extracts structured data, and persists the result in the database.

    This function handles the core logic for an individual post:
    - Retrieves necessary information (ID, URL, critic ID) from the page dictionary.
    - Calls the appropriate asynchronous parser based on the critic ID.
    - Validates the extracted data.
    - Maps the extracted data to the database schema.
    - Updates the database with the parsed content or logs an error if parsing fails.
    - Increments metrics and logs the outcome of the parsing attempt.

    Args:
        session (aiohttp.ClientSession): The aiohttp client session for making HTTP requests.
        page (dict): A dictionary containing the raw page data, including 'id', 'page_url', and 'critic_id'.
        step_logger (StepLogger): The logger instance for tracking step-specific metrics and logs.
        attempt (int): The current attempt number for parsing this page (used for retries).
    """
    page_id = page["id"]
    page_url = page["page_url"]
    critic_id = page["critic_id"]

    # Basic validation to ensure essential data is present before proceeding.
    if not all([page_id, critic_id, page_url]):
        step_logger.logger.error(f"Skipping post with missing data: {page}")
        # Log this as a failure in the pipeline, as it's an unprocessable item.
        log_step_result(
            "parse_post",
            link_id=page_id,
            attempt_number=attempt,
            status="failure",
            error_message="Missing essential data (ID, critic_id, or URL)",
        )
        return

    try:
        # Acquire a semaphore to limit concurrent requests.
        async with semaphore:
            # Set a timeout for the parsing operation to prevent indefinite hangs.
            async with async_timeout.timeout(10):
                # Call the dynamic parser dispatcher to get structured data from the page.
                # The parse_post_async function internally selects the correct critic parser.
                data = await parse_post_async(session, page_url, critic_id)

        # Validate that all expected keys are present in the parsed data.
        # This ensures the parser returned a complete set of information.
        for key in ["url", "title", "summary", "full_review", "date"]:
            if key not in data:
                raise ValueError(f"Missing {key} in parsed data")

        # Map the parsed data keys to the database column names.
        # This ensures consistency with the Supabase schema.
        parsed_data = {
            "parsed_title": data["title"],
            "parsed_short_review": data["summary"],
            "parsed_full_review": data["full_review"],
            "parsed_review_date": data["date"],
        }

        # Update the database record for the raw page with the extracted content and 'parsed' status.
        update_page_as_parsed(page_id, parsed_data)
        step_logger.metrics["saved_count"] += 1
        step_logger.logger.info("Stored review from %s", page_url)
        
        # Log the successful parsing of this specific link in the pipeline logs.
        log_step_result(
            "parse_post",
            link_id=page_id,
            attempt_number=attempt,
            status="success",
            result_data={"link": page_url},
        )
    except Exception as e:
        # Log a warning for failed attempts, including the URL and error message.
        step_logger.logger.warning(
            "Attempt %s failed for %s: %s", attempt, page_url, e
        )
        # Update the database record to mark the page as failed and store the error details.
        update_page_with_error(page_id, type(e).__name__, str(e))
        
        # Log the parsing failure in the pipeline logs.
        log_step_result(
            "parse_post",
            link_id=page_id,
            attempt_number=attempt,
            status="failure",
            error_message=str(e),
        )
        # Re-raise the exception to be caught by the retry mechanism (run_with_retries).
        raise

async def parse_posts(pages: list[dict]) -> None:
    """
    Orchestrates the parsing and storage of a list of raw blog post entries.

    This function manages the overall parsing process:
    - Initializes a StepLogger for the entire parsing step.
    - Fetches all 'pending' raw pages from the database.
    - Creates and manages asynchronous tasks for parsing each page concurrently.
    - Applies retry logic for individual parsing attempts.
    - Processes results, logs failures, and updates metrics.

    Args:
        pages (list[dict]): A list of dictionaries, each representing a raw page entry to be parsed.
    """
    # Initialize a StepLogger for the entire parsing step (Step 2).
    step_logger = StepLogger("step_2_parse_posts")
    
    # If no pages are provided, log and finalize immediately.
    if not pages:
        step_logger.logger.info("No new posts to parse")
        step_logger.finalize()
        return
    
    # Record the total number of posts to be processed.
    step_logger.metrics["input_count"] = len(pages)
    step_logger.logger.info("Parsing %s posts", step_logger.metrics["input_count"])

    # Use an aiohttp ClientSession for efficient and persistent HTTP connections.
    async with aiohttp.ClientSession() as session:
        # Create a list of asynchronous tasks, each wrapped with retry logic.
        # Each task will call _parse_and_store for a single page.
        tasks = [
            run_with_retries(
                _parse_and_store,
                args=[session, page, step_logger],
                max_retries=MAX_RETRIES,
            )
            for page in pages
        ]
        # Run all tasks concurrently and gather their results.
        # return_exceptions=True ensures that exceptions are returned as results,
        # rather than stopping the entire gather operation.
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process the results of each parsing task.
    for result, page in zip(results, pages):
        # If a task resulted in an exception (meaning all retries failed).
        if isinstance(result, Exception):
            step_logger.metrics["failed_count"] += 1
            # Log the failure with full traceback for detailed debugging.
            step_logger.logger.error("Failed to parse %s", page["page_url"], exc_info=True)
            # Write the failed URL and error message to a dedicated failure file.
            write_failure("failed_post_links.txt", page["page_url"], str(result))
            # Log the final failure in the pipeline logs after all retries.
            log_step_result(
                "parse_post",
                link_id=page.get("id"),
                attempt_number=MAX_RETRIES, # Log with the max retries attempted
                status="failure",
                error_message=str(result),
            )

    # Calculate the total number of processed items.
    step_logger.metrics["processed_count"] = step_logger.metrics["saved_count"] + step_logger.metrics["failed_count"]
    step_logger.logger.info("Parsing complete")
    # Finalize the step logger, which typically writes metrics to a log file or database.
    step_logger.finalize()

if __name__ == "__main__":
    # This block allows the orchestrator to be run directly for testing or standalone execution.
    # It fetches pending pages and initiates the asynchronous parsing process.
    pages_to_parse = get_pending_pages_to_parse()
    asyncio.run(parse_posts(pages_to_parse))