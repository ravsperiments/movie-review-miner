"""Step 2: parse blog posts and store them in Supabase."""
import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm

from crawler.scraper.parse_post import parse_post_async
from crawler.db.store_scraped_pages import get_pending_pages_to_parse, update_page_as_parsed, update_page_with_error
from crawler.utils.io_helpers import write_failure
from crawler.utils import StepLogger
from crawler.utils.retries import run_with_retries
from crawler.db.pipeline_logger import log_step_result
import json


CONCURRENT_REQUESTS = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _parse_and_store(
    session: aiohttp.ClientSession,
    page: dict,
    step_logger: StepLogger,
    reviewer: str,
    attempt: int = 1,
) -> None:
    """Parse a blog post URL and persist the result."""
    page_id = page["id"]
    page_url = page["page_url"]
    try:
        async with semaphore:
            async with async_timeout.timeout(10):
                data = await parse_post_async(session, page_url, reviewer)

        for key in ["url", "title", "summary", "full_review", "date"]:
            if key not in data:
                raise ValueError(f"Missing {key}")

        parsed_data = {
            "parsed_title": data["title"],
            "parsed_short_review": data["summary"],
            "parsed_full_review": data["full_review"],
            "parsed_review_date": data["date"],
        }

        update_page_as_parsed(page_id, parsed_data)
        step_logger.metrics["saved_count"] += 1
        step_logger.logger.info("Stored review from %s", page_url)
        log_step_result(
            "parse_post",
            link_id=page_id,
            attempt_number=attempt,
            status="success",
            result_data={"link": page_url},
        )
    except Exception as e:
        step_logger.logger.warning(
            "Attempt %s failed for %s: %s", attempt, page_url, e
        )
        update_page_with_error(page_id, type(e).__name__, str(e))
        log_step_result(
            "parse_post",
            link_id=page_id,
            attempt_number=attempt,
            status="failure",
            error_message=str(e),
        )
        raise

async def parse_posts(pages: list[dict], reviewer: str = "baradwajrangan") -> None:
    """Parse and store a list of blog post URLs."""
    step_logger = StepLogger("step_2_parse_posts")
    if not pages:
        step_logger.logger.info("No new posts to parse")
        step_logger.finalize()
        return
    
    step_logger.metrics["input_count"] = len(pages)
    step_logger.logger.info("Parsing %s posts", step_logger.metrics["input_count"])
    async with aiohttp.ClientSession() as session:
        tasks = [
            run_with_retries(
                _parse_and_store,
                args=[session, page, step_logger, reviewer],
                max_retries=MAX_RETRIES,
            )
            for page in pages
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result, page in zip(results, pages):
        if isinstance(result, Exception):
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.error("Failed to parse %s", page["page_url"], exc_info=True)
            write_failure("failed_post_links.txt", page["page_url"], str(result))
            log_step_result(
                "parse_post",
                link_id=page.get("id"),
                attempt_number=MAX_RETRIES,
                status="failure",
                error_message=str(result),
            )

    step_logger.metrics["processed_count"] = step_logger.metrics["saved_count"] + step_logger.metrics["failed_count"]
    step_logger.logger.info("Parsing complete")
    step_logger.finalize()

if __name__ == "__main__":
    pages_to_parse = get_pending_pages_to_parse()
    asyncio.run(parse_posts(pages_to_parse))
