import argparse
import asyncio
import aiohttp
import async_timeout
import os
from tqdm import tqdm

from crawler.fetch_links import get_post_links_async
from crawler.parse_post import parse_post
from db.store_review import store_review
from db.review_queries import get_latest_post_date, get_links_after_date
from llm.openai_wrapper import is_film_review
from utils.logger import get_logger

logger = get_logger(__name__)

# Config
CONCURRENT_FETCHES = 10
MAX_RETRIES = 3
FAILED_LINKS_FILE = "failed_links.txt"
semaphore = asyncio.Semaphore(CONCURRENT_FETCHES)

def append_failed_link(url: str):
    """Append a failed link to failed_links.txt without duplication."""
    try:
        existing = set()
        if os.path.exists(FAILED_LINKS_FILE):
            with open(FAILED_LINKS_FILE, "r") as f:
                existing = set(line.strip() for line in f)

        if url not in existing:
            with open(FAILED_LINKS_FILE, "a") as f:
                f.write(url + "\n")
    except Exception as e:
        logger.error(f"⚠️ Could not record failed link {url}: {e}")

async def fetch_post_html(session, url: str):
    """Fetch HTML content of a blog post with retries and exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                async with async_timeout.timeout(10):
                    async with session.get(url) as response:
                        html = await response.text()
                        return url, html
        except Exception as e:
            logger.warning(f"⚠️ Attempt {attempt} failed for {url}: {e}")
            await asyncio.sleep(2 ** (attempt - 1))

    logger.error(f"❌ Giving up on {url} after {MAX_RETRIES} attempts")
    append_failed_link(url)
    return url, None

async def crawl_blog_links(start=1, end=279, batch_size=50):
    """Main batched async crawl from blog listing pages."""
    existing_links = set()
    try:
        latest_post_date = get_latest_post_date()
        existing_links = get_links_after_date(latest_post_date) if latest_post_date else set()
    except Exception as e:
        logger.error("⚠️ Failed to fetch existing links: %s", e)

    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        logger.info(f"🚀 Crawling pages {batch_start} to {batch_end}...")

        post_links = await get_post_links_async(batch_start, batch_end)
        links_to_fetch = [link for _, _, link in post_links if link not in existing_links]

        if not links_to_fetch:
            logger.info("✅ All links already processed in this batch.")
            continue

        async with aiohttp.ClientSession() as session:
            fetch_tasks = [fetch_post_html(session, link) for link in links_to_fetch]
            post_html_results = await asyncio.gather(*fetch_tasks)

        for link, html in tqdm(post_html_results, desc=f"Processing batch {batch_start}-{batch_end}"):
            if not html:
                continue  # already logged and recorded

            try:
                extracted_text = parse_post(link, html=html)
                if not extracted_text:
                    logger.warning("⚠️ No content extracted from %s", link)
                    continue

                if not is_film_review(extracted_text["title"], extracted_text["short_review"]):
                    logger.info("⏭️ Skipped non-movie review: %s", link)
                    continue

                review = {
                    "blog_title": extracted_text["title"],
                    "post_date": extracted_text["post_date"] or None,
                    "short_review": extracted_text["short_review"],
                    "full_excerpt": extracted_text["full_review"],
                    "link": link,
                }

                store_review(review)
                logger.info("✅ Stored review: %s", link)

            except Exception as e:
                logger.error("❌ Failed to parse/store %s: %s", link, e)

        await asyncio.sleep(1)  # polite delay

async def retry_failed_links():
    """Reprocess links from failed_links.txt"""
    if not os.path.exists(FAILED_LINKS_FILE):
        logger.info("No failed_links.txt found. Nothing to retry.")
        return

    with open(FAILED_LINKS_FILE, "r") as f:
        failed_links = [line.strip() for line in f if line.strip()]

    if not failed_links:
        logger.info("✅ No failed links left to retry.")
        return

    logger.info(f"🔁 Retrying {len(failed_links)} failed links...")

    async with aiohttp.ClientSession() as session:
        fetch_tasks = [fetch_post_html(session, link) for link in failed_links]
        post_html_results = await asyncio.gather(*fetch_tasks)

    for link, html in tqdm(post_html_results, desc="Retrying failed links"):
        if not html:
            continue

        try:
            extracted_text = parse_post(link, html=html)
            if not extracted_text:
                logger.warning("⚠️ No content extracted from %s", link)
                continue

            if not is_film_review(extracted_text["title"], extracted_text["short_review"]):
                logger.info("⏭️ Skipped non-movie review: %s", link)
                continue

            review = {
                "blog_title": extracted_text["title"],
                "post_date": extracted_text["post_date"] or None,
                "short_review": extracted_text["short_review"],
                "full_excerpt": extracted_text["full_review"],
                "link": link,
            }

            store_review(review)
            logger.info("✅ Stored review (retry): %s", link)

        except Exception as e:
            logger.error("❌ Retry failed on %s: %s", link, e)

def parse_args():
    parser = argparse.ArgumentParser(description="Async blog crawler")
    parser.add_argument("--start", type=int, default=1, help="Start page number")
    parser.add_argument("--end", type=int, default=279, help="End page number")
    parser.add_argument("--batch-size", type=int, default=50, help="Pages per batch")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed_links.txt instead of fresh crawl")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.retry_failed:
        asyncio.run(retry_failed_links())
    else:
        asyncio.run(crawl_blog_links(start=args.start, end=args.end, batch_size=args.batch_size))
