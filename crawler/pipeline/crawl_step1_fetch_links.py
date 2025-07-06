"""Step 1: fetch blog post links from the source site and save in supabase."""
import asyncio
from crawler.scraper.fetch_links import get_post_links_async
from db.store_review import store_blog_post_urls
from utils import StepLogger


async def fetch_links(start_page: int = 1, end_page: int = 279, reviewer: str = "baradwajrangan") -> list[str]:
    """Fetch blog post links and persist them."""
    step_logger = StepLogger("step_1_fetch_links")
    await get_post_links_async(start_page, end_page, reviewer)
    step_logger.logger.info("Attempted to fetch and store links.")
    step_logger.finalize()
    return []

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(fetch_links())
