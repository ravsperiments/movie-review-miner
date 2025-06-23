import requests
from bs4 import BeautifulSoup

BASE_URL = "https://baradwajrangan.wordpress.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_post_links(max_pages=5, max_links=100):
    links = []

    for page_num in range(1, max_pages + 1):
        url = f"{BASE_URL}/page/{page_num}/"
        print(f"\n📄 Page {page_num}: Scanning {url}")

        try:
            res = requests.get(url, headers=HEADERS)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            count_before = len(links)
            for a in soup.select("div.post h2 a[rel='bookmark']"):
                href = a.get('href')
                if href and href not in links:
                    links.append(href)
                    print(f"✅ Found: {href}")
                if len(links) >= max_links:
                    break

            count_after = len(links)
            print(f"📝 Collected {count_after - count_before} new links (Total: {count_after})")

            if len(links) >= max_links:
                break

        except Exception as e:
            print(f"❌ Error on page {page_num}: {e}")
            break

    return links
