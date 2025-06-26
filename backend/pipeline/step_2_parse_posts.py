"""Step 2: parse blog posts and store them in Supabase."""
import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm
from crawler.parse_post import parse_post_async
from db.store_review import store_review_if_missing
from utils.logger import get_logger
from utils.io_helpers import write_failure

logger = get_logger(__name__)

CONCURRENT_REQUESTS = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _parse_and_store(session: aiohttp.ClientSession, url: str) -> None:
    """Parse a blog post URL and persist the result."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                async with async_timeout.timeout(10):
                    data = await parse_post_async(session, url)
            review = {
                "link": data["url"],
                "blog_title": data["title"],
                "short_review": data["summary"],
                "full_excerpt": data["full_review"],
                "post_date": data["date"],
            }
            store_review_if_missing(review)
            logger.info("Stored review from %s", url)
            return
        except Exception as e:
            logger.warning("Attempt %s failed for %s: %s", attempt, url, e)
            await asyncio.sleep(2 ** (attempt - 1))
    logger.error("Failed to parse %s", url, exc_info=True)
    write_failure("failed_post_links.txt", url, "max retries")

async def parse_posts(urls: list[str]) -> None:
    """Parse and store a list of blog post URLs."""
    if not urls:
        logger.info("No new posts to parse")
        return
    logger.info("Parsing %s posts", len(urls))
    async with aiohttp.ClientSession() as session:
        tasks = [_parse_and_store(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = sum(isinstance(r, Exception) for r in results)
        if failures:
            logger.error("%s posts failed to parse", failures)
        logger.info("Parsing complete")
