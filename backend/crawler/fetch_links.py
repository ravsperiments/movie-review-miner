"""Utilities for scraping blog post links from Baradwaj Rangan's site."""

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from utils.logger import get_logger

# Base address of the WordPress blog to crawl
BASE_URL = "https://baradwajrangan.wordpress.com"
# Minimal headers so our requests look like those of a browser
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Module level logger reused by all functions
logger = get_logger(__name__)


def get_post_links(max_pages: int = 5, start_page: int = 1, start_index: int = 0):
    """Yield blog post links starting from the given page and index.

    Args:
        max_pages: Highest listing page number to crawl.
        start_page: Which page to begin crawling from.
        start_index: Index on the start page from which to resume.

    Yields:
        A tuple of ``(page_num, idx, url)`` for each discovered post.
    """

    for page_num in range(start_page, max_pages + 1):
        url = f"{BASE_URL}/page/{page_num}/"
        logger.info("Scanning %s", url)

        try:
            # Retrieve the HTML for the listing page
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
        except RequestException as e:
            # Stop crawling if any page fails to load
            logger.error("Error fetching page %s: %s", page_num, e)
            break

        soup = BeautifulSoup(res.text, "html.parser")

        # Links to individual posts live inside <h2> tags under div.post
        link_tags = soup.select("div.post h2 a[rel='bookmark']")
        for idx, a in enumerate(link_tags):
            # Skip links on the first page until we reach the start index
            if page_num == start_page and idx < start_index:
                continue
            href = a.get("href")
            if href:
                logger.debug("Found link: %s", href)
                yield page_num, idx, href


