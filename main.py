from crawler.fetch_links import get_post_links
from crawler.parse_post import parse_post
from llm.openai_wrapper import is_film_review, analyze_sentiment
from utils.db import init_db, save_post, fetch_unanalyzed, update_recommendation
from utils.state import load_state, save_state

MAX_PAGES = 5


def crawl_and_store() -> None:
    state = load_state()
    for page, idx, link in get_post_links(max_pages=MAX_PAGES, start_page=state["page"], start_index=state["index"]):
        print(f"\n🔗 {link}")
        try:
            data = parse_post(link)
            if not data["short_review"] and not data["full_review"]:
                print("⚠️  No review content. Skipping.")
                continue
            review_check = is_film_review(data["title"], data["short_review"])
            print(f"🔎 Review Check: {review_check}")
            if review_check.lower().startswith("yes"):
                save_post(
                    {
                        "link": link,
                        "date": data["date"],
                        "title": data["title"],
                        "reviewer": data["reviewer"],
                        "subtext": data["short_review"],
                        "full_review": data["full_review"],
                        "recommendation": None,
                    }
                )
        except Exception as e:
            print(f"❌ Error processing {link}: {e}")
        finally:
            save_state({"page": page, "index": idx + 1})

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

def analyze_db() -> None:
    for link, review in fetch_unanalyzed():
        try:
            sentiment = analyze_sentiment(review)
            update_recommendation(link, sentiment)
            print(f"🤖 Sentiment for {link}: {sentiment}")
        except Exception as e:
            print(f"❌ Sentiment failed for {link}: {e}")


def main() -> None:
    init_db()
    crawl_and_store()
    analyze_db()


if __name__ == "__main__":
    main()

