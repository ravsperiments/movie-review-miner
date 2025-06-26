"""Step 1: fetch blog post links from the source site and save in supabase."""
import asyncio
from crawler.fetch_links import get_post_links_async
from db.store_review import store_blog_post_urls
from utils.logger import get_logger

logger = get_logger(__name__)

async def fetch_links(start_page: int = 1, end_page: int = 279) -> list[str]:
    links = await get_post_links_async(start_page, end_page)
    logger.info("Discovered %s new links", len(links))

    stored = 0
    for link in links:
        try:
            store_blog_post_urls({"link": link[2], "blog_title": "TBD"})
            stored += 1
        except Exception as e:
            logger.warning("Failed to store link: %s (%s)", link, e)

    logger.info("Stored %s links to DB", stored)
    return links

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(fetch_links())
