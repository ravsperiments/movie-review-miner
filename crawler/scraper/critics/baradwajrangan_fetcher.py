"""Step 1: fetch blog post links from the source site and save in supabase."""
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from crawler.scraper.fetch_links import get_post_links_async
from crawler.db.store_scraped_pages import bulk_insert_raw_urls
from crawler.utils import StepLogger

async def fetch_links(critic_id: str, base_url: str, domain: str, start_page: int = 1, end_page: int = 279) -> list[str]:
    """Fetch blog post links and persist them."""
    step_logger = StepLogger(f"step_1_fetch_links_{domain.replace('.', '_')}")
    
    # This function now returns a list of tuples: (page, index, url)
    fetched_links_tuples = await get_post_links_async(start_page, end_page, domain.split('.')[0])
    
    pages_data = []
    for _, _, url in fetched_links_tuples:
        pages_data.append({
            "page_url": url,
            "base_url": base_url,
            "critic_id": critic_id,
            "fetched_at": datetime.utcnow().isoformat(),
            "status": "pending"
        })
        
    if pages_data:
        bulk_insert_raw_urls(pages_data)
        
    step_logger.logger.info(f"Attempted to fetch and store {len(pages_data)} links for {domain}.")
    step_logger.finalize()
    return [item['page_url'] for item in pages_data]

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    # This block is for testing the specific fetcher in isolation
    # In a real scenario, this would be called by the orchestrator
    test_critic_id = "79031f4e-3785-425d-a17d-4796cdf0a87e"
    test_base_url = "https://baradwajrangan.wordpress.com/"
    test_domain = "baradwajrangan.wordpress.com"
    asyncio.run(fetch_links(test_critic_id, test_base_url, test_domain))
