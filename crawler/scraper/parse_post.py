"""
Dispatcher for parsing blog posts from different film critics.

This module acts as a router that delegates blog post parsing to critic-specific
parsers based on the reviewer ID or name. It supports extensibility for adding
new critics by registering their parsers in the SOURCES mapping.
"""

import aiohttp
from .critics import baradwajrangan_parser as baradwajrangan_parse

# Mapping of critic IDs to their specialized parsers
SOURCES = {
    "bf1be5bb-fa08-4b90-a391-02b46d3cfd18": baradwajrangan_parse,  # Baradwaj Rangan
}


async def parse_post_async(session: aiohttp.ClientSession, url: str, reviewer: str = "baradwajrangan") -> dict:
    """
    Parse a single blog post URL using the appropriate critic-specific parser.

    Routes the parsing request to the correct parser based on the reviewer identifier.
    Each parser is responsible for extracting structured data from a critic's blog
    post format, including title, short review, full review excerpt, publish date, etc.

    Args:
        session: An aiohttp.ClientSession for making HTTP requests.
        url: The full URL of the blog post to parse.
        reviewer: The reviewer identifier (default: "baradwajrangan").
                  Matches keys in the SOURCES dictionary.

    Returns:
        dict: A dictionary containing the parsed blog post data with keys such as:
            - title: The post's title
            - short_review: A brief summary
            - full_excerpt: The main review content
            - publish_date: Publication timestamp
            - url: The original post URL

    Raises:
        ValueError: If the reviewer is not found in SOURCES.
        Exception: May raise exceptions from the underlying aiohttp session or parser.
    """
    source = SOURCES.get(reviewer)
    if not source:
        raise ValueError(f"Unknown reviewer: {reviewer}")
    return await source.parse_post_async(session, url)
