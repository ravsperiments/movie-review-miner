"""Step 1: fetch blog post links from the source site and save in supabase."""
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from crawler.scraper.fetch_links import get_post_links_async
from crawler.db.store_scraped_pages import bulk_insert_raw_urls
from crawler.utils import StepLogger

async def fetch_links(critic_id: str, base_url: str, domain: str, start_page: int = 1, end_page: int = 279) -> list[str]:
    """
    Fetches blog post links for a specific critic and persists them in the database.

    This function orchestrates the scraping of post links from a given critic's domain,
    prepares the data with relevant metadata (critic ID, base URL, fetched timestamp),
    and then stores these raw URLs in the Supabase database for further processing.

    Args:
        critic_id (str): The unique identifier for the critic.
        base_url (str): The base URL of the critic's blog/website.
        domain (str): The domain name of the critic's website (e.g., "baradwajrangan.wordpress.com").
        start_page (int, optional): The starting page number for scraping. Defaults to 1.
        end_page (int, optional): The ending page number for scraping. Defaults to 279.

    Returns:
        list[str]: A list of the URLs of the fetched pages.
    """
    # Initialize a StepLogger for detailed logging of this specific fetching operation.
    # The logger name includes the domain to differentiate logs for different critics.
    step_logger = StepLogger(f"step_1_fetch_links_{domain.replace('.', '_')}")
    
    # Asynchronously fetch post links from the critic's domain.
    # get_post_links_async returns a list of tuples: (page_number, index_on_page, url).
    # We pass the simplified domain (e.g., "baradwajrangan" from "baradwajrangan.wordpress.com")
    # as the 'reviewer' argument to match the expected input of get_post_links_async.
    fetched_links_tuples = await get_post_links_async(start_page, end_page, domain.split('.')[0])
    
    # Prepare the fetched data for bulk insertion into the database.
    # Each link is augmented with critic-specific metadata and a 'pending' status.
    pages_data = []
    for _, _, url in fetched_links_tuples:
        pages_data.append({
            "page_url": url,
            "base_url": base_url,
            "critic_id": critic_id,
            "fetched_at": datetime.utcnow().isoformat(), # Timestamp of when the link was fetched
            "status": "pending" # Initial status for newly fetched links
        })
        
    # If any links were fetched, perform a bulk insert operation to store them in Supabase.
    if pages_data:
        bulk_insert_raw_urls(pages_data)
        
    # Log the number of links that were attempted to be fetched and stored.
    step_logger.logger.info(f"Attempted to fetch and store {len(pages_data)} links for {domain}.")
    
    # Finalize the logging for this step, indicating its completion.
    step_logger.finalize()
    
    # Return only the URLs of the fetched pages.
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
