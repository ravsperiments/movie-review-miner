"""Step 2: parse blog posts and store them in Supabase."""
import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm

from crawler.parse_post import parse_post_async
from db.store_review import store_review_if_missing
from db.review_queries import get_links_with_title_tbd
from utils.io_helpers import write_failure
from utils import StepLogger
from db.pipeline_logger import log_step_result
import json


CONCURRENT_REQUESTS = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _parse_and_store(
    session: aiohttp.ClientSession, url: str, step_logger: StepLogger
) -> None:
    """Parse a blog post URL and persist the result."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                async with async_timeout.timeout(10):
                    data = await parse_post_async(session, url["link"])
            review = {
                "link": data["url"],
                "blog_title": data["title"],
                "short_review": data["summary"],
                "full_excerpt": data["full_review"],
                "post_date": data["date"],
            }
            store_review_if_missing(review)
            step_logger.metrics["saved_count"] += 1
            step_logger.logger.info("Stored review from %s", url)
            log_step_result(
                "parse_post",
                link_id=url.get("id"),
                attempt_number=attempt,
                status="success",
                result_data={"link": review["link"]},
            )
            return
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
            await asyncio.sleep(2 ** (attempt - 1))
    step_logger.metrics["failed_count"] += 1
    step_logger.logger.error("Failed to parse %s", url["link"], exc_info=True)
    write_failure("failed_post_links.txt", url["link"], "max retries")

async def parse_posts(urls: list[str]) -> None:
    """Parse and store a list of blog post URLs."""
    step_logger = StepLogger("step_2_parse_posts")
    if not urls:
        step_logger.logger.info("No new posts to parse")
        step_logger.finalize()
        return
    step_logger.metrics["input_count"] = len(urls)
    step_logger.logger.info("Parsing %s posts", len(urls))
    async with aiohttp.ClientSession() as session:
        tasks = [_parse_and_store(session, url, step_logger) for url in urls]
        await asyncio.gather(*tasks, return_exceptions=True)
    step_logger.metrics["processed_count"] = step_logger.metrics["saved_count"] + step_logger.metrics["failed_count"]
    step_logger.logger.info("Parsing complete")
    step_logger.finalize()

if __name__ == "__main__":
    urls = get_links_with_title_tbd()
    print(f"[DEBUG] URLs from DB: {urls[0]}")
    asyncio.run(parse_posts(urls))
