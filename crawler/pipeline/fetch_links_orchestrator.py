import asyncio
import importlib
from crawler.db.critic_queries import get_critics
from crawler.utils import StepLogger

async def orchestrate_fetch_links():
    """
    Orchestrates the fetching of blog post links for all configured reviewers.

    This function serves as the central control point for the first step of the
    data pipeline. It retrieves the list of reviewers, and for each reviewer,
    it dynamically loads and executes their specific link-fetching logic.
    This design allows for easy addition of new reviewers with unique scraping
    requirements without modifying the core orchestration logic.
    """
    # Initialize a StepLogger for the orchestration process. This provides
    # consistent logging for the overall link fetching step.
    step_logger = StepLogger("fetch_links_orchestrator")
    
    # Retrieve the list of reviewers from the designated source.
    # In the current implementation, this comes from a hardcoded list,
    # but it's designed to be extensible to fetch from a database (e.g., Supabase).
    critics = get_critics()

    # Iterate through each reviewer to initiate their link fetching process.
    for critic in critics:
        # Extract relevant details for the current reviewer.
        critic_id = critic["id"]
        base_url = critic["base_url"]
        domain = urlparse(base_url).netloc
        
        # Construct the module name for the reviewer-specific fetcher script.
        # The naming convention is 'crawler.scraper.critics.<domain_prefix>_fetcher'.
        # For example, 'baradwajrangan.wordpress.com' becomes 'baradwajrangan_fetcher'.
        module_name = f"crawler.scraper.critics.{domain.split('.')[0]}_fetcher"

        try:
            # Dynamically import the reviewer-specific fetcher module.
            # This allows the orchestrator to call different scraping logic
            # based on the reviewer without explicit conditional statements.
            fetcher_module = importlib.import_module(module_name)
            
            # Call the 'fetch_links' asynchronous function from the imported module.
            # This function is responsible for the actual scraping and initial storage
            # of raw page URLs for the specific critic.
            await fetcher_module.fetch_links(critic_id, base_url, domain)
            
            # Log successful completion for the current reviewer.
            step_logger.logger.info(f"Successfully fetched links for {critic['name']} ({domain}).")
        except ImportError:
            # Log an error if the expected fetcher module for a reviewer is not found.
            # This indicates a misconfiguration or missing script.
            step_logger.logger.error(f"Fetcher module not found for {critic['name']}: {module_name}")
        except Exception as e:
            # Catch and log any other exceptions that occur during the fetching process
            # for a specific reviewer. This ensures that a failure for one reviewer
            # does not halt the entire orchestration process.
            step_logger.logger.error(f"Error fetching links for {critic['name']} ({domain}): {e}")
    
    # Finalize the logger for the entire orchestration step.
    step_logger.finalize()

if __name__ == "__main__":
    # This block allows the orchestrator to be run directly for testing or standalone execution.
    # It initiates the asynchronous orchestration process.
    asyncio.run(orchestrate_fetch_links())
