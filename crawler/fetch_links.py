import requests
from bs4 import BeautifulSoup

BASE_URL = "https://baradwajrangan.wordpress.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_post_links(max_pages=5, start_page=1, start_index=0):
    """Yield blog post links one by one starting from the given page/index."""
    for page_num in range(start_page, max_pages + 1):
        url = f"{BASE_URL}/page/{page_num}/"
        print(f"\n📄 Page {page_num}: Scanning {url}")

        try:
            res = requests.get(url, headers=HEADERS)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            link_tags = soup.select("div.post h2 a[rel='bookmark']")
            for idx, a in enumerate(link_tags):
                if page_num == start_page and idx < start_index:
                    continue
                href = a.get("href")
                if href:
                    print(f"✅ Found: {href}")
                    yield page_num, idx, href
        except Exception as e:
            print(f"❌ Error on page {page_num}: {e}")
            break

