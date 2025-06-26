"""Step 2: parse blog posts and store them in Supabase."""
import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm
from crawler.parse_post import parse_post_async
from db.store_review import store_review_if_missing
from utils.logger import StepLogger
from utils.io_helpers import write_failure

CONCURRENT_REQUESTS = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def _parse_and_store(
    session: aiohttp.ClientSession, url: str, slog: StepLogger
) -> None:
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
            slog.logger.info("Stored review from %s", url)
            slog.processed()
            slog.saved()
            return
        except Exception as e:
            slog.logger.warning("Attempt %s failed for %s: %s", attempt, url, e)
            await asyncio.sleep(2 ** (attempt - 1))
    slog.logger.error("Failed to parse %s", url, exc_info=True)
    slog.processed()
    slog.failed()
    write_failure("failed_post_links.txt", url, "max retries")

async def parse_posts(urls: list[str]) -> None:
    """Parse and store a list of blog post URLs."""
    slog = StepLogger("step_2_parse_posts")
    slog.set_input_count(len(urls))
    if not urls:
        slog.note("No new posts to parse")
        slog.finalize()
        return
    slog.logger.info("Parsing %s posts", len(urls))
    async with aiohttp.ClientSession() as session:
        tasks = [_parse_and_store(session, url, slog) for url in urls]
        await asyncio.gather(*tasks, return_exceptions=True)
    slog.logger.info("Parsing complete")
    slog.finalize()


if __name__ == "__main__":
    import sys
    import warnings

    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(parse_posts(sys.argv[1:]))
