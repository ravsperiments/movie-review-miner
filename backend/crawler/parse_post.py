"""Dispatcher for parsing blog posts from different reviewers."""
import aiohttp
from .sources import baradwajrangan_parse

SOURCES = {
    "baradwajrangan": baradwajrangan_parse,
}

async def parse_post_async(session: aiohttp.ClientSession, url: str, reviewer: str = "baradwajrangan") -> dict:
    """Parse a single blog post URL for the given reviewer."""
    source = SOURCES.get(reviewer)
    if not source:
        raise ValueError(f"Unknown reviewer: {reviewer}")
    return await source.parse_post_async(session, url)
