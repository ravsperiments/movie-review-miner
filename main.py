from crawler.fetch_links import get_post_links
from crawler.parse_post import parse_post
from llm.openai_wrapper import is_film_review, analyze_sentiment, extract_movie_title
from db.store_review import store_review

MAX_PAGES = 1
MAX_LINKS = 100


def crawl_and_store():
    links = list(get_post_links(max_pages=MAX_PAGES))
    print(f"\n📦 Total collected: {len(links)} post links.\n")

    curated = []  # ✅ Important: define before usage

    for page_num, idx, link in links:
        print(f"\n🔗 [{idx+1}/{len(links)}] {link}")
        try:
            data = parse_post(link)

            if not data.get("short_review") and not data.get("full_review"):
                print("⚠️  Skipping: No review content found.\n")
                continue

            reviewer = data.get("reviewer") or "Unknown"

            # Step 1: Check if it's a review
            review_check = is_film_review(data["title"], data["short_review"])
            print(f"🔎 Review Check: {review_check}")

            if not review_check.lower().startswith("yes"):
                print("⏭️ Skipping: Not a review post.\n")
                continue

            # Step 2: Extract movie title with fallback
            try:
                movie_title = extract_movie_title(data['title'])
                if movie_title.lower() == "none":
                    movie_title = None
                print(movie_title)
            except Exception as e:
                print(f"⚠️ Error extracting movie title from: {data['title']} — {e}")
                movie_title = None

            # Step 3: Sentiment analysis
            try:
                sentiment_raw = analyze_sentiment(data["full_review"], data["short_review"])
                sentiment = sentiment_raw.strip().split()[0]  # Get only Yes/No/Maybe
            except Exception as e:
                print(f"❌ Sentiment analysis failed: {e}")
                sentiment = None

            print(f"✅ RECOMMENDED")
            print(f"Blog Title: {data['title']} by {reviewer}\n")
            print(f"Movie Title: {movie_title}\n")
            print(f"Sentiment: {sentiment}\n")
            print(f"Short Review:\n{data['short_review']}\n")
            print(f"Full Review Excerpt:\n{data['full_review']}\n")

            if sentiment is not None:
                store_review({
                    "blog_title": data['title'],
                    "movie_title": movie_title,
                    "link": link,
                    "sentiment": sentiment,
                    "short_review": data['short_review'],
                    "full_excerpt": data['full_review'],
                    "reviewer": "BR"
                })

        except Exception as e:
            print(f"❌ Error processing {link}: {e}")


def main():
    print("🎬 Starting Movie Review Miner...\n")
    crawl_and_store()


if __name__ == "__main__":
    main()
