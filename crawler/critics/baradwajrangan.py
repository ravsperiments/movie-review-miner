"""
Baradwaj Rangan blog scraper - fetches links and parses reviews.

This module handles all scraping for the Baradwaj Rangan WordPress blog:
- Fetching blog post links from listing pages
- Parsing individual blog posts to extract review content
- Orchestrating the fetch + store workflow
"""
import asyncio
import argparse
import json
import sys
from datetime import datetime
from urllib.parse import urljoin

import aiohttp
import httpx
import requests
from bs4 import BeautifulSoup

from crawler.utils.logger import get_logger
from crawler.utils.io_helpers import write_failure
from crawler.db.scraper_queries import get_all_urls, bulk_insert_raw_urls
from crawler.utils import StepLogger

logger = get_logger(__name__)

# Base URL for the Baradwaj Rangan blog
BASE_URL = "https://baradwajrangan.wordpress.com"

# Concurrency settings
CONCURRENT_FETCHES = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_FETCHES)

# HTTP headers to mimic a browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# =============================================================================
# LINK FETCHING - Extract blog post URLs from listing pages
# =============================================================================

def extract_links_from_html(html: str, page: int) -> list[tuple[int, int, str]]:
    """
    Extract blog post links from a listing page HTML.

    Args:
        html: The HTML content of the listing page.
        page: The page number.

    Returns:
        List of (page_number, index_on_page, url) tuples.
    """
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select(
        "div.featured_content h2 a[rel='bookmark'], div.post h2 a[rel='bookmark']"
    )
    return [
        (page, idx, urljoin(BASE_URL, a["href"]))
        for idx, a in enumerate(anchors)
        if a.get("href")
    ]


async def fetch_listing_page(client: httpx.AsyncClient, page: int) -> list[tuple[int, int, str]]:
    """
    Fetch a single listing page and extract post links.

    Args:
        client: The httpx async client.
        page: The page number to fetch.

    Returns:
        List of extracted links, empty if all retries fail.
    """
    url = BASE_URL if page == 1 else f"{BASE_URL}/page/{page}/"
    logger.info("Fetching %s", url)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.get(url, headers=HEADERS, timeout=30.0)
            html = response.text

            if page == 1 and attempt == 1:
                with open("crawler/debug_page_1.html", "w") as f:
                    f.write(html)

            logger.info("Page %s attempt %s length=%s", page, attempt, len(html))
            return extract_links_from_html(html, page)

        except Exception as e:
            logger.warning("Attempt %s failed for page %s: %s", attempt, page, e)
            await asyncio.sleep(2 ** (attempt - 1))

    logger.error("Giving up on page %s after %s retries", page, MAX_RETRIES)
    write_failure("failed_pages.txt", str(page), "max retries")
    return []


async def get_post_links_async(start_page: int = 1, end_page: int = 279) -> list[tuple[int, int, str]]:
    """
    Fetch blog post links within a page range, with early stopping.

    Stops early if a page contains no new links (all already in DB).

    Args:
        start_page: Starting page number.
        end_page: Ending page number.

    Returns:
        List of (page_number, index_on_page, url) for new links.
    """
    recent_links = get_all_urls()
    all_links: list[tuple[int, int, str]] = []

    # Force HTTP/1.1 - WordPress.com has issues with HTTP/2
    async with httpx.AsyncClient(http1=True, http2=False, follow_redirects=True) as client:
        for page in range(start_page, end_page + 1):
            page_links = await fetch_listing_page(client, page)
            found_new_link_on_page = False

            for triple in page_links:
                if triple[2] not in recent_links:
                    all_links.append(triple)
                    found_new_link_on_page = True
                else:
                    logger.info("Skipping known link: %s", triple[2])

            if not found_new_link_on_page:
                logger.info("No new links found on page %s. Stopping early.", page)
                break

    logger.info("Fetched total of %s links before early stop or completion", len(all_links))
    return all_links


def get_post_links(page: int) -> list[str]:
    """
    Sync wrapper for fetching links from a single page.
    """
    async def run():
        async with httpx.AsyncClient(http1=True, http2=False, follow_redirects=True) as client:
            results = await fetch_listing_page(client, page)
            return [url for (_, _, url) in results]
    return asyncio.run(run())


# =============================================================================
# POST PARSING - Extract review content from individual blog posts
# =============================================================================

def parse_post(url: str) -> dict:
    """
    Synchronously parse a blog post URL.

    Args:
        url: The blog post URL.

    Returns:
        Dict with url, title, summary, date, full_review.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.select_one("#header-about h1")
    title = title.get_text(strip=True) if title else "unknown"

    date_text = soup.select_one(".date-comments em")
    date = date_text.get_text(strip=True).replace("Posted on ", "") if date_text else "unknown"

    short_review = ""
    entry_div = soup.select_one("div.entry")
    if entry_div:
        paragraphs = entry_div.find_all("p")
        if paragraphs:
            short_review = paragraphs[0].get_text(strip=True)

    full_review = ""
    if entry_div:
        paras = entry_div.find_all("p")
        filtered = [
            p.get_text(strip=True)
            for p in paras
            if not p.find("a") and "watch the trailer" not in p.get_text(strip=True).lower()
        ]
        full_review = "\n\n".join(filtered)

    return {
        "url": url,
        "title": title,
        "summary": short_review,
        "date": date,
        "full_review": full_review,
    }


async def parse_post_async(session: aiohttp.ClientSession, url: str) -> dict:
    """
    Asynchronously parse a blog post URL.

    Args:
        session: The aiohttp client session.
        url: The blog post URL.

    Returns:
        Dict with url, title, summary, date, full_review.
    """
    async with session.get(url, timeout=10) as response:
        response.raise_for_status()
        text = await response.text()
        soup = BeautifulSoup(text, "html.parser")

        title = soup.select_one("#header-about h1")
        title = title.get_text(strip=True) if title else "unknown"

        date_text = soup.select_one(".date-comments em")
        date = date_text.get_text(strip=True).replace("Posted on ", "") if date_text else "unknown"

        short_review = ""
        entry_div = soup.select_one("div.entry")
        if entry_div:
            paragraphs = entry_div.find_all("p")
            if paragraphs:
                short_review = paragraphs[0].get_text(strip=True)

        full_review = ""
        if entry_div:
            paras = entry_div.find_all("p")
            filtered = [
                p.get_text(strip=True)
                for p in paras
                if not p.find("a") and "watch the trailer" not in p.get_text(strip=True).lower()
            ]
            full_review = "\n\n".join(filtered)

        return {
            "url": url,
            "title": title,
            "summary": short_review,
            "date": date,
            "full_review": full_review,
        }


# =============================================================================
# ORCHESTRATION - Fetch links and store to DB
# =============================================================================

async def fetch_links(
    critic_id: str,
    base_url: str,
    domain: str,
    start_page: int = 1,
    end_page: int = 279,
) -> list[str]:
    """
    Fetch blog post links and persist them in the database.

    Args:
        critic_id: The critic's unique identifier.
        base_url: The base URL of the critic's blog.
        domain: The domain name (e.g., "baradwajrangan.wordpress.com").
        start_page: Starting page number.
        end_page: Ending page number.

    Returns:
        List of fetched page URLs.
    """
    step_logger = StepLogger(f"step_1_fetch_links_{domain.replace('.', '_')}")

    fetched_links_tuples = await get_post_links_async(start_page, end_page)

    pages_data = []
    for _, _, url in fetched_links_tuples:
        pages_data.append({
            "page_url": url,
            "base_url": base_url,
            "critic_id": critic_id,
            "fetched_at": datetime.utcnow().isoformat(),
            "status": "pending",
        })

    if pages_data:
        bulk_insert_raw_urls(pages_data)

    step_logger.logger.info(f"Attempted to fetch and store {len(pages_data)} links for {domain}.")
    step_logger.finalize()

    return [item["page_url"] for item in pages_data]


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="URL of a blog post to parse")
    parser.add_argument("--fetch-links", action="store_true", help="Fetch links mode")
    args = parser.parse_args()

    if args.url:
        try:
            print(f"[DEBUG] Parsing {args.url}", file=sys.stderr, flush=True)
            post_data = parse_post(args.url)
            print(json.dumps(post_data), flush=True)
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr, flush=True)
            exit(1)
    elif args.fetch_links:
        test_critic_id = "79031f4e-3785-425d-a17d-4796cdf0a87e"
        test_base_url = "https://baradwajrangan.wordpress.com/"
        test_domain = "baradwajrangan.wordpress.com"
        asyncio.run(fetch_links(test_critic_id, test_base_url, test_domain))
