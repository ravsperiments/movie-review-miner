"""Step 1: fetch blog post links from the source site and save in supabase."""
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from crawler.scraper.fetch_links import get_post_links_async
from crawler.db.store_scraped_pages import bulk_insert_raw_urls
from crawler.utils import StepLogger

# Known critics mapping
KNOWN_CRITICS = {
    "baradwajrangan.wordpress.com": {
        "id": "79031f4e-3785-425d-a17d-4796cdf0a87e",
        "name": "Baradwaj Rangan",
        "base_url": "https://baradwajrangan.wordpress.com/"
    }
}

def get_critic_id_from_url(url: str) -> Optional[str]:
    for domain, critic in KNOWN_CRITICS.items():
        if domain in url:
            return critic["id"]
    return None

async def fetch_links(start_page: int = 1, end_page: int = 279, reviewer: str = "baradwajrangan") -> list[str]:
    """Fetch blog post links and persist them."""
    step_logger = StepLogger("step_1_fetch_links")
    
    # This function now returns a list of tuples: (page, index, url)
    fetched_links_tuples = await get_post_links_async(start_page, end_page, reviewer)
    
    pages_data = []
    for _, _, url in fetched_links_tuples:
        critic_id = get_critic_id_from_url(url)
        base_url = urlparse(url).netloc
        pages_data.append({
            "page_url": url,
            "base_url": base_url,
            "critic_id": critic_id,
            "fetched_at": datetime.utcnow().isoformat(),
            "status": "pending"
        })
        
    if pages_data:
        bulk_insert_raw_urls(pages_data)
        
    step_logger.logger.info(f"Attempted to fetch and store {len(pages_data)} links.")
    step_logger.finalize()
    return [item['page_url'] for item in pages_data]

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(fetch_links())
