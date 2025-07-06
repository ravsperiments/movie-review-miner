import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from utils.logger import get_logger
from utils.io_helpers import write_failure
from db.review_queries import get_latest_post_date, get_recent_links

BASE_URL = "https://baradwajrangan.wordpress.com"
CONCURRENT_FETCHES = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_FETCHES)

logger = get_logger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

def extract_links_from_html(html: str, page: int) -> list[tuple[int, int, str]]:
    soup = BeautifulSoup(html, "html.parser")

    anchors = soup.select(
        "div.featured_content h2 a[rel='bookmark'], div.post h2 a[rel='bookmark']"
    )

    return [
        (page, idx, urljoin(BASE_URL, a["href"]))
        for idx, a in enumerate(anchors)
        if a.get("href")
    ]

async def fetch_listing_page(session: aiohttp.ClientSession, page: int) -> list[tuple[int, int, str]]:
    url = BASE_URL if page == 1 else f"{BASE_URL}/page/{page}/"
    logger.info("Fetching %s", url)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=HEADERS) as response:
                        html = await response.text()

                        if page == 1 and attempt == 1:
                            with open("debug_page_1.html", "w") as f:
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
    Fetch blog post links between start_page and end_page.
    Stops early if a recent link (already stored) is encountered.
    """
    recent_links = get_recent_links()

    connector = aiohttp.TCPConnector(limit=CONCURRENT_FETCHES)
    all_links: list[tuple[int, int, str]] = []

    async with aiohttp.ClientSession(connector=connector) as session:
        for page in range(start_page, end_page + 1):
            page_links = await fetch_listing_page(session, page)

            for triple in page_links:
                if triple[2] in recent_links:
                    logger.info("Encountered known link: %s — stopping fetch early.", triple[2])
                    return all_links
                all_links.append(triple)

    logger.info("Fetched total of %s links before early stop or completion", len(all_links))
    return all_links

def get_post_links(page: int) -> list[str]:
    """
    Sync wrapper for fetch_listing_page(). Used in RQ jobs.
    """
    async def run():
        async with aiohttp.ClientSession() as session:
            results = await fetch_listing_page(session, page)
            return [url for (_, _, url) in results]

    return asyncio.run(run())
