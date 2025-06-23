from crawler.fetch_links import get_post_links
from crawler.parse_post import parse_post
from llm.openai_wrapper import is_film_review, analyze_sentiment

MAX_PAGES = 1
MAX_LINKS = 100

def main():
    print("🔍 Fetching post links...")
    links = get_post_links(max_pages=MAX_PAGES, max_links=MAX_LINKS)
    print(f"\n📦 Total collected: {len(links)} post links.\n")

    curated = []

    for i, link in enumerate(links):
        print(f"\n🔗 [{i+1}/{len(links)}] {link}")
        try:
            data = parse_post(link)

            if not data["short_review"] and not data["full_review"]:
                print("⚠️  Skipping: No review content found.\n")
                continue

            # Step 1: Check if it's a review
            review_check = is_film_review(data["title"], data["short_review"])
            print(f"🔎 Review Check: {review_check}")

            if not review_check.lower().startswith("yes"):
                print("⏭️ Skipping: Not a review post.\n")
                continue

            # Step 2: Sentiment analysis using title and subtext
            sentiment = analyze_sentiment(data["title"], data["short_review"])
            print(f"🤖 Sentiment: {sentiment}\n")

            # Only keep recommended movies
            if sentiment.lower().startswith("yes"):
                curated.append({
                    "title": data["title"],
                    "link": link,
                    "sentiment": sentiment,
                    "short_review": data["short_review"],
                    "excerpt": data["full_review"]
                })

                # Output recommendation immediately
                print(f"✅ RECOMMENDED")
                print(f"Title: {data['title']}\n")
                print(f"Short Review:\n{data['short_review']}\n")
                print(f"Full Review Excerpt:\n{data['full_review']}\n")

        except Exception as e:
            print(f"❌ Error processing {link}: {e}")

    # Final summary
    print("\n🎯 Curated Recommendations:")
    for movie in curated:
        print(f"- {movie['title']} ({movie['sentiment']})")
        print(f"  {movie['link']}\n")

if __name__ == "__main__":
    main()
