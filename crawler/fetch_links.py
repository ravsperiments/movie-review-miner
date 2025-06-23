import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from utils.logger import get_logger

BASE_URL = "https://baradwajrangan.wordpress.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

logger = get_logger(__name__)


def get_post_links(max_pages=5, start_page=1, start_index=0):
    """Yield blog post links one by one starting from the given page/index."""
    for page_num in range(start_page, max_pages + 1):
        url = f"{BASE_URL}/page/{page_num}/"
        logger.info("Scanning %s", url)

        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
        except RequestException as e:
            logger.error("Error fetching page %s: %s", page_num, e)
            break

        soup = BeautifulSoup(res.text, "html.parser")

        link_tags = soup.select("div.post h2 a[rel='bookmark']")
        for idx, a in enumerate(link_tags):
            if page_num == start_page and idx < start_index:
                continue
            href = a.get("href")
            if href:
                logger.debug("Found link: %s", href)
                yield page_num, idx, href

