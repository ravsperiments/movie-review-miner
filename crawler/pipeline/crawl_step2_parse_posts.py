"""Step 2: parse blog posts and store them in Supabase."""
import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm

from crawler.scraper.parse_post import parse_post_async
from db.review_queries import get_links_with_title_tbd
from db.crud import upsert_review
from utils.io_helpers import write_failure
from utils import StepLogger
from utils.retries import run_with_retries
from db.pipeline_logger import log_step_result
import json


CONCURRENT_REQUESTS = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _parse_and_store(
    session: aiohttp.ClientSession,
    url: dict,
    step_logger: StepLogger,
    reviewer: str,
    attempt: int = 1,
) -> None:
    """Parse a blog post URL and persist the result."""
    try:
        async with semaphore:
            async with async_timeout.timeout(10):
                data = await parse_post_async(session, url["link"], reviewer)

        for key in ["url", "title", "summary", "full_review", "date"]:
            if key not in data:
                raise ValueError(f"Missing {key}")

        review = {
            "link": data["url"],
            "blog_title": data["title"],
            "short_review": data["summary"],
            "full_excerpt": data["full_review"],
            "post_date": data["date"],
        }

        await upsert_review(review)
        step_logger.metrics["saved_count"] += 1
        step_logger.logger.info("Stored review from %s", url["link"])
        log_step_result(
            "parse_post",
            link_id=url.get("id"),
            attempt_number=attempt,
            status="success",
            result_data={"link": review["link"]},
        )
    except Exception as e:
        step_logger.logger.warning(
            "Attempt %s failed for %s: %s", attempt, url["link"], e
        )
        log_step_result(
            "parse_post",
            link_id=url.get("id"),
            attempt_number=attempt,
            status="failure",
            error_message=str(e),
        )
        raise

async def parse_posts(urls: list[str], reviewer: str = "baradwajrangan") -> None:
    """Parse and store a list of blog post URLs."""
    step_logger = StepLogger("step_2_parse_posts")
    if not urls:
        step_logger.logger.info("No new posts to parse")
        step_logger.finalize()
        return
    unique = {u["link"]: u for u in urls}.values()
    step_logger.metrics["input_count"] = len(list(unique))
    step_logger.logger.info("Parsing %s posts", step_logger.metrics["input_count"])
    async with aiohttp.ClientSession() as session:
        tasks = [
            run_with_retries(
                _parse_and_store,
                args=[session, url, step_logger, reviewer],
                max_retries=MAX_RETRIES,
            )
            for url in unique
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result, url in zip(results, unique):
        if isinstance(result, Exception):
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.error("Failed to parse %s", url["link"], exc_info=True)
            write_failure("failed_post_links.txt", url["link"], str(result))
            log_step_result(
                "parse_post",
                link_id=url.get("id"),
                attempt_number=MAX_RETRIES,
                status="failure",
                error_message=str(result),
            )

    step_logger.metrics["processed_count"] = step_logger.metrics["saved_count"] + step_logger.metrics["failed_count"]
    step_logger.logger.info("Parsing complete")
    step_logger.finalize()

if __name__ == "__main__":
    urls = get_links_with_title_tbd()
    asyncio.run(parse_posts(urls))
