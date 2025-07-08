"""Dispatcher for parsing blog posts from different reviewers."""
import aiohttp
from .critics import baradwajrangan_parser as baradwajrangan_parse

SOURCES = {
    "79031f4e-3785-425d-a17d-4796cdf0a87e": baradwajrangan_parse, # Baradwaj Rangan
}

async def parse_post_async(session: aiohttp.ClientSession, url: str, reviewer: str = "baradwajrangan") -> dict:
    """Parse a single blog post URL for the given reviewer."""
    source = SOURCES.get(reviewer)
    if not source:
        raise ValueError(f"Unknown reviewer: {reviewer}")
    return await source.parse_post_async(session, url)
