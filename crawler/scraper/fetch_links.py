"""Dispatcher for fetching blog post links from different reviewers.

This module acts as a central dispatcher for initiating the scraping of
blog post links from various reviewer sources. It maps a simplified reviewer
identifier to the specific scraping logic implemented for that reviewer.
"""
from .sources import baradwajrangan_links

# A dictionary mapping simplified reviewer names to their respective
# link-fetching modules. This allows for easy extension to new reviewers
# by adding new entries and corresponding modules in the 'sources' directory.
SOURCES = {
    "baradwajrangan": baradwajrangan_links, # Maps 'baradwajrangan' to its specific scraping module.
}

async def get_post_links_async(start_page: int = 1, end_page: int = 279, reviewer: str = "baradwajrangan") -> list[tuple[int, int, str]]:
    """
    Asynchronously fetches blog post links for a specified reviewer.

    This function serves as the public interface for initiating link scraping.
    It looks up the appropriate scraping module based on the 'reviewer' argument
    and delegates the actual fetching task to that module.

    Args:
        start_page (int, optional): The starting page number for scraping.
                                    Defaults to 1.
        end_page (int, optional): The ending page number for scraping.
                                  Defaults to 279.
        reviewer (str, optional): The simplified name of the reviewer whose
                                  links are to be fetched (e.g., "baradwajrangan").
                                  Defaults to "baradwajrangan".

    Returns:
        list[tuple[int, int, str]]: A list of tuples, where each tuple contains
                                    (page_number, index_on_page, url) of a fetched link.

    Raises:
        ValueError: If an unknown or unsupported reviewer is provided.
    """
    # Retrieve the specific scraping module for the given reviewer.
    source = SOURCES.get(reviewer)
    
    # If no module is found for the reviewer, raise an error.
    if not source:
        raise ValueError(f"Unknown reviewer: {reviewer}")
        
    # Delegate the link fetching to the specific reviewer's module.
    # This module contains the concrete implementation of how to scrape
    # links from that reviewer's website.
    return await source.get_post_links_async(start_page, end_page)
