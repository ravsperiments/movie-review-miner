import asyncio
import importlib
from crawler.db.reviewers import get_reviewers
from crawler.utils import StepLogger

async def orchestrate_fetch_links():
    step_logger = StepLogger("fetch_links_orchestrator")
    reviewers = get_reviewers()

    for reviewer in reviewers:
        critic_id = reviewer["id"]
        base_url = reviewer["base_url"]
        domain = reviewer["domain"]
        module_name = f"crawler.scraper.critics.{domain.split('.')[0]}_fetcher"

        try:
            # Dynamically import the reviewer-specific fetcher module
            fetcher_module = importlib.import_module(module_name)
            # Call the fetch_links function from the imported module
            await fetcher_module.fetch_links(critic_id, base_url, domain)
            step_logger.logger.info(f"Successfully fetched links for {reviewer['name']} ({domain}).")
        except ImportError:
            step_logger.logger.error(f"Fetcher module not found for {reviewer['name']}: {module_name}")
        except Exception as e:
            step_logger.logger.error(f"Error fetching links for {reviewer['name']} ({domain}): {e}")
    
    step_logger.finalize()

if __name__ == "__main__":
    asyncio.run(orchestrate_fetch_links())
