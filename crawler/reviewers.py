"""Registry of available reviewers for crawling."""

from dataclasses import dataclass
from typing import Callable, Awaitable, List

import aiohttp
from scraper.fetch_links import SOURCES as LINK_SOURCES
from scraper.parse_post import SOURCES as PARSE_SOURCES


@dataclass
class Reviewer:
    id: str
    base_url: str
    link_source: Callable[[int, int], Awaitable[List[tuple[int, int, str]]]]
    parse_source: Callable[[aiohttp.ClientSession, str], Awaitable[dict]]


REVIEWERS: dict[str, Reviewer] = {
    "baradwajrangan": Reviewer(
        id="baradwajrangan",
        base_url="https://baradwajrangan.wordpress.com",
        link_source=LINK_SOURCES["baradwajrangan"].get_post_links_async,
        parse_source=PARSE_SOURCES["baradwajrangan"].parse_post_async,
    ),
}
