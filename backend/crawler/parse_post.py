import argparse
import json
import requests
from bs4 import BeautifulSoup
import re
import sys

# --- SYNC version (unchanged) ---
def parse_post(url: str) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    print("parse_post")

    # Extract title
    title = soup.select_one("#header-about h1")
    title = title.get_text(strip=True) if title else "unknown"

    # Extract date
    date_text = soup.select_one(".date-comments em")
    date = date_text.get_text(strip=True).replace("Posted on ", "") if date_text else "unknown"

    # Extract short review (first paragraph inside .entry)
    short_review = ""
    entry_div = soup.select_one("div.entry")
    if entry_div:
        paragraphs = entry_div.find_all("p")
        if paragraphs:
            short_review = paragraphs[0].get_text(strip=True)

    # Extract full review (all <p> in .entry except trailer/links)
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
        "full_review": full_review
    }

# --- ASYNC version for batch processing ---
import aiohttp

async def parse_post_async(session: aiohttp.ClientSession, url: str) -> dict:
    async with session.get(url, timeout=10) as response:
        print("in parse_post")
        response.raise_for_status()
        text = await response.text()
        soup = BeautifulSoup(text, "html.parser")
      

        # Extract title
        title = soup.select_one("#header-about h1")
        title = title.get_text(strip=True) if title else "unknown"

        # Extract date
        date_text = soup.select_one(".date-comments em")
        date = date_text.get_text(strip=True).replace("Posted on ", "") if date_text else "unknown"

        # Extract short review (first paragraph inside .entry)
        short_review = ""
        entry_div = soup.select_one("div.entry")
        if entry_div:
            paragraphs = entry_div.find_all("p")
            if paragraphs:
                short_review = paragraphs[0].get_text(strip=True)

        # Extract full review (all <p> in .entry except trailer/links)
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
            "full_review": full_review
        }

# --- CLI for sync version ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="URL of the blog post")
    args = parser.parse_args()
    print(args.url)
    try:
        print(f"[DEBUG] Parsing {args.url}", file=sys.stderr, flush=True)
        post_data = parse_post(args.url)
        print(json.dumps(post_data), flush=True)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        exit(1)
