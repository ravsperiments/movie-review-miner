"""Step 1: fetch blog post links from the source site."""
import asyncio
from crawler.fetch_links import get_post_links_async
from db.review_queries import get_latest_post_date, get_links_after_date
from utils.logger import get_logger

logger = get_logger(__name__)

async def fetch_links(start_page: int = 1, end_page: int = 279) -> list[str]:
    """Fetch new blog post links skipping ones already stored."""
    logger.info("Fetching links from pages %s to %s", start_page, end_page)
    latest_date = get_latest_post_date()
    existing_links = get_links_after_date(latest_date) if latest_date else set()
    logger.info("Loaded %s existing links", len(existing_links))

    links = await get_post_links_async(start_page, end_page)
    new_links = [link for _, _, link in links if link not in existing_links]
    logger.info("Discovered %s new links", len(new_links))
    return new_links
