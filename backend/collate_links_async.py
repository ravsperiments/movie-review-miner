"""Asynchronous crawler that stores blog links into Supabase."""

import asyncio
import requests
from bs4 import BeautifulSoup

from crawler.fetch_links import get_post_links
from crawler.parse_post import parse_post
from db.store_review import store_review
from db.supabase_client import supabase
from llm.openai_wrapper import is_film_review
from utils.logger import get_logger
from db.review_queries import get_latest_post_date, get_links_after_date

logger = get_logger(__name__)

def extract_post_text(html: str) -> str:
    """Extract main text content from a blog post HTML."""
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("div.post")
    return content.get_text(separator="\n", strip=True) if content else ""

async def crawl_blog_links():
    """Crawl blog pages and persist new review links."""

    # Fetch all existing links from Supabase
    existing_links = set()
    try:
        latest_post_date = get_latest_post_date()
        existing_links = get_links_after_date(latest_post_date) if latest_post_date else set()
        
    except Exception as e:
        logger.error("Failed to fetch existing links: %s", e)

    for page, idx, link in get_post_links(max_pages=1):
        if link in existing_links:
            logger.info("🛑 Reached existing link, stopping: %s", link)
            break

        try:
            res = requests.get(link, timeout=10)
            res.raise_for_status()
            extracted_text = parse_post(link)
            print(extracted_text)

            if not extracted_text:
                logger.warning("No content extracted from %s", link)
                continue

            if not is_film_review(extracted_text["title"], extracted_text["short_review"]):
                logger.info("❌ Skipped non-movie review: %s", link)
                continue

            review = {
                "blog_title": extracted_text["title"],
                "post_date": extracted_text["post_date"] if extracted_text["post_date"] else None,
                "short_review": extracted_text["short_review"],
                "full_excerpt": extracted_text["full_review"],
                "link": link,
            }

            store_review(review)
            logger.info("✅ Stored review: %s", link)

        except Exception as e:
            logger.error("❌ Failed to process %s: %s", link, e)

if __name__ == "__main__":
    asyncio.run(crawl_blog_links())
