"""Dispatcher for fetching blog post links from different reviewers."""
from .sources import baradwajrangan_links

SOURCES = {
    "baradwajrangan": baradwajrangan_links,
}

async def get_post_links_async(start_page: int = 1, end_page: int = 279, reviewer: str = "baradwajrangan") -> list[tuple[int, int, str]]:
    """Fetch blog post links for the given reviewer."""
    source = SOURCES.get(reviewer)
    if not source:
        raise ValueError(f"Unknown reviewer: {reviewer}")
    return await source.get_post_links_async(start_page, end_page)
