import argparse
import asyncio
import json
from tqdm import tqdm

from crawler.fetch_links import get_post_links_async
from utils.logger import get_logger

logger = get_logger(__name__)
OUTPUT_FILE = "all_blog_links.json"

async def extract_and_save_links(start: int, end: int, batch_size: int):
    all_links = []

    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        logger.info(f"🚀 Crawling listing pages {batch_start} to {batch_end}...")

        links = await get_post_links_async(start_page=batch_start, end_page=batch_end)

        for page, idx, url in tqdm(links, desc=f"Batch {batch_start}-{batch_end}"):
            all_links.append({"page": page, "index": idx, "link": url})

    logger.info(f"✅ Total extracted links: {len(all_links)}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_links, f, indent=2)

    logger.info(f"💾 Saved to {OUTPUT_FILE}")

def parse_args():
    parser = argparse.ArgumentParser(description="Extract blog post links into a local file")
    parser.add_argument("--start", type=int, default=1, help="Start page number")
    parser.add_argument("--end", type=int, default=279, help="End page number")
    parser.add_argument("--batch-size", type=int, default=50, help="Pages per batch")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(extract_and_save_links(args.start, args.end, args.batch_size))
