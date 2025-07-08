import asyncio
import aiohttp
import async_timeout
from tqdm.asyncio import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from crawler.utils.logger import get_logger
from crawler.utils.io_helpers import write_failure
from crawler.db.store_scraped_pages import get_all_urls

# Base URL for the Baradwaj Rangan blog, used for constructing full URLs.
BASE_URL = "https://baradwajrangan.wordpress.com"

# Maximum number of concurrent HTTP fetches to prevent overwhelming the server.
CONCURRENT_FETCHES = 10

# Maximum number of retries for fetching a single page in case of transient errors.
MAX_RETRIES = 3

# Semaphore to control the concurrency of asynchronous requests.
# This ensures that no more than CONCURRENT_FETCHES requests are active at any given time.
semaphore = asyncio.Semaphore(CONCURRENT_FETCHES)

# Initialize a logger for this module to record events, warnings, and errors.
logger = get_logger(__name__)

# Standard HTTP headers to mimic a web browser, helping to avoid being blocked by websites.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

def extract_links_from_html(html: str, page: int) -> list[tuple[int, int, str]]:
    """
    Extracts blog post links from the given HTML content of a listing page.

    This function parses the HTML using BeautifulSoup and identifies specific
    anchor tags that correspond to individual blog post links. It constructs
    full URLs and associates them with their page number and an index on that page.

    Args:
        html (str): The HTML content of the blog listing page.
        page (int): The page number from which the HTML was extracted.

    Returns:
        list[tuple[int, int, str]]: A list of tuples, where each tuple contains
                                    (page_number, index_on_page, full_url) of a blog post.
    """
    # Parse the HTML content using BeautifulSoup.
    soup = BeautifulSoup(html, "html.parser")

    # Select anchor tags that are within specific div and h2 elements.
    # These selectors are tailored to the structure of the Baradwaj Rangan blog.
    anchors = soup.select(
        "div.featured_content h2 a[rel='bookmark'], div.post h2 a[rel='bookmark']"
    )

    # Iterate through the found anchor tags, extract their href attributes,
    # and construct full URLs using urljoin. Filter out any empty hrefs.
    return [
        (page, idx, urljoin(BASE_URL, a["href"]))
        for idx, a in enumerate(anchors)
        if a.get("href")
    ]

async def fetch_listing_page(session: aiohttp.ClientSession, page: int) -> list[tuple[int, int, str]]:
    """
    Asynchronously fetches a single blog listing page and extracts links.

    This function handles the HTTP request to a specific page of the blog,
    including retries for transient network issues. It then calls
    `extract_links_from_html` to parse the content and return the found links.

    Args:
        session (aiohttp.ClientSession): The aiohttp client session to use for the request.
        page (int): The page number to fetch.

    Returns:
        list[tuple[int, int, str]]: A list of extracted links from the page.
                                    Returns an empty list if fetching fails after retries.
    """
    # Construct the URL for the current page. Page 1 uses the base URL directly.
    url = BASE_URL if page == 1 else f"{BASE_URL}/page/{page}/"
    logger.info("Fetching %s", url)

    # Implement a retry mechanism for fetching the page.
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Acquire a semaphore to limit concurrent fetches.
            async with semaphore:
                # Set a timeout for the HTTP request to prevent indefinite hangs.
                async with async_timeout.timeout(10):
                    # Perform the GET request to the constructed URL.
                    async with session.get(url, headers=HEADERS) as response:
                        # Read the response body as text.
                        html = await response.text()

                        # For debugging purposes, save the HTML of the first page on the first attempt.
                        if page == 1 and attempt == 1:
                            with open("crawler/debug_page_1.html", "w") as f:
                                f.write(html) # Corrected: use html variable instead of response.text

                        logger.info("Page %s attempt %s length=%s", page, attempt, len(html))
                        # Extract and return links from the fetched HTML.
                        return extract_links_from_html(html, page)

        except Exception as e:
            # Log a warning if an attempt fails and wait before retrying.
            logger.warning("Attempt %s failed for page %s: %s", attempt, page, e)
            # Exponential backoff: wait longer with each subsequent retry.
            await asyncio.sleep(2 ** (attempt - 1))

    # If all retries fail, log an error and record the failure.
    logger.error("Giving up on page %s after %s retries", page, MAX_RETRIES)
    write_failure("failed_pages.txt", str(page), "max retries")
    return []

async def get_post_links_async(start_page: int = 1, end_page: int = 279) -> list[tuple[int, int, str]]:
    """
    Fetches blog post links for the Baradwaj Rangan blog within a specified page range.

    This is the main asynchronous function for scraping links. It iterates through
    pages, fetches links, and implements an early stopping mechanism: if a page
    contains no new links (i.e., all links found on that page have already been
    scraped in a previous run), the scraping process stops to avoid redundant work.

    Args:
        start_page (int, optional): The starting page number for scraping. Defaults to 1.
        end_page (int, optional): The ending page number for scraping. Defaults to 279.

    Returns:
        list[tuple[int, int, str]]: A list of unique, newly found blog post links,
                                    each as a tuple (page_number, index_on_page, full_url).
    """
    # Retrieve a set of all URLs already present in the database.
    # This is used to identify and skip already processed links.
    recent_links = get_all_urls()

    # Configure a TCP connector for the aiohttp session to manage connection limits.
    connector = aiohttp.TCPConnector(limit=CONCURRENT_FETCHES)
    
    # List to store all newly fetched links.
    all_links: list[tuple[int, int, str]] = []

    # Create an aiohttp client session for making HTTP requests.
    async with aiohttp.ClientSession(connector=connector) as session:
        # Iterate through the specified page range.
        for page in range(start_page, end_page + 1):
            # Fetch links from the current listing page.
            page_links = await fetch_listing_page(session, page)

            # Flag to track if any new links were found on the current page.
            found_new_link_on_page = False
            
            # Process each link found on the current page.
            for triple in page_links:
                # Check if the link is already in the set of recent (known) links.
                if triple[2] not in recent_links:
                    # If it's a new link, add it to the list of all fetched links.
                    all_links.append(triple)
                    found_new_link_on_page = True
                else:
                    # If the link is already known, log that it's being skipped.
                    logger.info("Skipping known link: %s", triple[2])
            
            # Implement early stopping: if no new links were found on the current page,
            # it's assumed that subsequent pages will also not contain new links.
            if not found_new_link_on_page:
                logger.info("No new links found on page %s. Stopping early.", page)
                break

    # Log the total number of links fetched before stopping or completion.
    logger.info("Fetched total of %s links before early stop or completion", len(all_links))
    return all_links

def get_post_links(page: int) -> list[str]:
    """
    Synchronous wrapper for `fetch_listing_page()`.

    This function provides a synchronous interface to the asynchronous
    `fetch_listing_page` function. It's primarily used in contexts where
    asynchronous execution is not directly supported, such as certain
    task queues (e.g., RQ jobs).

    Args:
        page (int): The page number to fetch.

    Returns:
        list[str]: A list of URLs extracted from the specified page.
    """
    async def run():
        # Create a new aiohttp session for this synchronous call.
        async with aiohttp.ClientSession() as session:
            # Fetch links asynchronously and extract only the URLs.
            results = await fetch_listing_page(session, page)
            return [url for (_, _, url) in results]

    # Run the asynchronous `run` function using asyncio.run().
    return asyncio.run(run())
