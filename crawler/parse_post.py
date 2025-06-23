import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_post(url, max_chars=1200):
    """
    Fetches a blog post and returns:
    - Title
    - Short review blurb (1st paragraph)
    - Full review excerpt (2nd paragraph and beyond)
    """
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # Extract Title
    title_tag = soup.select_one("div#header-about h1")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Extract date
    date_tag = soup.select_one("time.entry-date") or soup.select_one("span.published")
    post_date = date_tag.get_text(strip=True) if date_tag else ""

    # Extract reviewer name if present
    author_tag = (
        soup.select_one("span.author a")
        or soup.select_one("a[rel='author']")
        or soup.select_one("span.fn")
    )
    reviewer = author_tag.get_text(strip=True) if author_tag else ""

    # Extract review paragraphs
    content_div = soup.select_one("div.entry")
    paragraphs = content_div.find_all("p") if content_div else []

    short_review = paragraphs[0].get_text(strip=True) if len(paragraphs) >= 1 else ""
    full_review = " ".join(p.get_text(strip=True) for p in paragraphs[1:])

    return {
        "title": title,
        "date": post_date,
        "reviewer": reviewer,
        "short_review": short_review,
        "full_review": full_review[:max_chars]
    }
