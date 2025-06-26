import asyncio
import aiohttp
import async_timeout
import json
import os
from tqdm import tqdm
import argparse

from crawler.parse_post import parse_post_async
from utils.logger import get_logger

logger = get_logger(__name__)
INPUT_FILE = "all_blog_links.json"
OUTPUT_FILE = "parsed_blog_posts.json"
FAILED_LINKS_FILE = "failed_post_links.txt"
CONCURRENT_REQUESTS = 10
MAX_RETRIES = 3

semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)


def load_links():
    with open(INPUT_FILE, "r") as f:
        return json.load(f)


def save_results(results):
    if not results:
        logger.info("🚫 No new posts to save.")
        return

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing = json.load(f)
    else:
        existing = []

    combined = existing + results
    with open(OUTPUT_FILE, "w") as f:
        json.dump(combined, f, indent=2)
    logger.info(f"💾 Saved {len(results)} posts to {OUTPUT_FILE}")


def append_failed_link(url: str):
    with open(FAILED_LINKS_FILE, "a") as f:
        f.write(url + "\n")


async def fetch_and_parse(session, url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                async with async_timeout.timeout(10):
                    return await parse_post_async(session, url["link"])
        except Exception as e:
            logger.warning(f"⚠️ Attempt {attempt} failed for {url}: {e}")
            await asyncio.sleep(2 ** (attempt - 1))

    logger.error(f"❌ Failed to parse {url} after {MAX_RETRIES} attempts")
    #append_failed_link(url)
    return None


async def extract_posts(start=0, end=None):
    logger.info("📥 Loading post URLs from %s...", INPUT_FILE)
    all_links = load_links()
    batch = all_links[start:end] if end else all_links[start:]
    logger.info(f"🚀 Extracting {len(batch)} posts from index {start} to {end or len(all_links)}...")

    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_parse(session, url) for url in batch]
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Parsing posts"):
            parsed = await coro
            if parsed:
                results.append(parsed)

    save_results(results)


def parse_args():
    parser = argparse.ArgumentParser(description="Extract and parse blog post content in batches.")
    parser.add_argument("--start", type=int, default=0, help="Start index in all_blog_links.json")
    parser.add_argument("--end", type=int, default=None, help="End index (non-inclusive)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(extract_posts(start=args.start, end=args.end))
