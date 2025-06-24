"""Helpers for downloading and parsing individual blog posts."""

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from utils.logger import get_logger

# Minimal headers so the request resembles that of a browser
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Module level logger to report parsing progress
logger = get_logger(__name__)


def parse_post(url: str, max_chars: int = 1200):
    """Return structured data extracted from a blog post.

    Args:
        url: The full URL of the post to parse.
        max_chars: Maximum number of characters of review text to return.

    Returns:
        A dictionary with keys ``title``, ``date``, ``reviewer``,
        ``short_review`` and ``full_review``.
    """
    try:
        # Retrieve the raw HTML for the post
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
    except RequestException as e:
        # Bubble up the error after logging it for visibility
        logger.error("Failed fetching %s: %s", url, e)
        raise

    # Parse the returned HTML
    soup = BeautifulSoup(res.text, "html.parser")

    # Extract the title from the header
    title_tag = soup.select_one("div#header-about h1")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Extract the publication date from <time> or <span class='published'>
    date_tag = soup.select_one("time.entry-date") or soup.select_one("span.published")
    post_date = date_tag.get_text(strip=True) if date_tag else ""

    # Extract the reviewer's name if one is mentioned
    author_tag = (
        soup.select_one("span.author a")
        or soup.select_one("a[rel='author']")
        or soup.select_one("span.fn")
    )
    reviewer = author_tag.get_text(strip=True) if author_tag else ""

    # Extract all paragraph tags from the main content
    content_div = soup.select_one("div.entry")
    paragraphs = content_div.find_all("p") if content_div else []

    # First paragraph often contains a short overview or teaser
    short_review = paragraphs[0].get_text(strip=True) if len(paragraphs) >= 1 else ""
    # Combine remaining paragraphs into the full review text
    full_review = " ".join(p.get_text(strip=True) for p in paragraphs[1:])

    logger.debug("Parsed post '%s' (%s chars)", title, len(full_review))

    return {
        "title": title,
        "date": post_date,
        "reviewer": reviewer,
        "short_review": short_review,
        "full_review": full_review[:max_chars]
    }
