"""Example asynchronous scraper used for testing concurrency."""

import asyncio
import httpx
from bs4 import BeautifulSoup

# Hard-coded list of blog URLs to scrape concurrently
BLOG_URLS = [
    "https://baradwajrangan.wordpress.com/2025/06/20/...",
    "https://baradwajrangan.wordpress.com/2025/06/16/...",
    # Add more blog URLs here
]

async def fetch_html(client, url):
    """Fetch HTML for a single URL using the provided client."""
    try:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        return url, response.text
    except httpx.HTTPError as e:
        print(f"❌ Error fetching {url}: {e}")
        return url, None

async def process_url(client, url):
    """Download and parse a single blog post."""
    url, html = await fetch_html(client, url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        # 👉 Extract title, review, etc.
        title = soup.title.text.strip()
        short_review = soup.find("p").text.strip()  # Example logic
        # Then pass to your existing pipeline:
        # if is_film_review(title, short_review): ...
        print(f"✅ Processed: {title}")
    else:
        print(f"⚠️ Skipped {url}")

async def main():
    """Kick off asynchronous scraping of all URLs."""
    async with httpx.AsyncClient() as client:
        tasks = [process_url(client, url) for url in BLOG_URLS]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
