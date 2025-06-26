"""Step 1: fetch blog post links from the source site."""
import asyncio
from crawler.fetch_links import get_post_links_async
from utils.logger import get_logger

logger = get_logger(__name__)

async def fetch_links(start_page: int = 1, end_page: int = 279) -> list[str]:
    links = await get_post_links_async(start_page, end_page)
    logger.info("Discovered %s new links", len(links))
    return links

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(fetch_links())