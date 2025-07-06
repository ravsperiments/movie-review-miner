"""Step 1: fetch blog post links from the source site and save in supabase."""
import asyncio
from crawler.fetch_links import get_post_links_async
from db.store_review import store_blog_post_urls
from utils import StepLogger


async def fetch_links(start_page: int = 1, end_page: int = 279, reviewer: str = "baradwajrangan") -> list[str]:
    """Fetch blog post links and persist them."""
    step_logger = StepLogger("step_1_fetch_links")
    links = await get_post_links_async(start_page, end_page, reviewer)
    step_logger.metrics["input_count"] = len(links)
    step_logger.logger.info("Discovered %s new links", len(links))

    processed_links = []
    for link in links:
        processed_links.append({"link": link[2]})
        step_logger.metrics["processed_count"] += 1
        try:
            store_blog_post_urls({"link": link[2], "blog_title": "TBD", "reviewer": reviewer})
            step_logger.metrics["saved_count"] += 1
        except Exception as e:
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.warning("Failed to store link: %s (%s)", link, e)

    step_logger.logger.info(
        "Stored %s links to DB", step_logger.metrics["saved_count"]
    )
    step_logger.finalize()
    return processed_links

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(fetch_links())
