import asyncio
import aiohttp
import async_timeout
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://baradwajrangan.wordpress.com"
CONCURRENT_FETCHES = 10
MAX_RETRIES = 3
semaphore = asyncio.Semaphore(CONCURRENT_FETCHES)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

def extract_links_from_html(html: str, page: int) -> list[tuple[int, int, str]]:
    soup = BeautifulSoup(html, "html.parser")

    # Combined selector for page 1 and paginated pages
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
    print(f"🌐 Fetching: {url}")  # log URL

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=HEADERS) as response:
                        print(f"✅ Status code for page {page}: {response.status}")
                        print(f"✅ Headers: {response.headers}")

                        html = await response.text()

                        print(f"✅ Fetched HTML length for page {page}: {len(html)}")
                        if page == 1 and attempt == 1:
                            with open("debug_page_1.html", "w") as f:
                                f.write(html)


                        print(f"📄 Page {page}, attempt {attempt}, length={len(html)}")

                        # Write debug file even if empty
                        if page == 1 and attempt == 1:
                            with open("debug_page_1.html", "w") as f:
                                f.write(html)

                        return extract_links_from_html(html, page)

        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed for page {page}: {e}")
            await asyncio.sleep(2 ** (attempt - 1))

    print(f"❌ Giving up on page {page} after {MAX_RETRIES} retries")
    return []


async def get_post_links_async(start_page: int = 1, end_page: int = 279) -> list[tuple[int, int, str]]:
    connector = aiohttp.TCPConnector(limit=CONCURRENT_FETCHES)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_listing_page(session, page) for page in range(start_page, end_page + 1)]
        results = await asyncio.gather(*tasks)
        all_links = [item for sublist in results for item in sublist]
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
