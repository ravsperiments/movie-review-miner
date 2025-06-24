"""Entry point for crawling the blog and storing curated reviews."""

from crawler.fetch_links import get_post_links
from crawler.parse_post import parse_post
from llm.openai_wrapper import is_film_review, analyze_sentiment, extract_movie_title
from db.store_review import store_review
from utils.logger import get_logger

# Configure crawling parameters
MAX_PAGES = 1
MAX_LINKS = 100

# Shared logger for this script
logger = get_logger(__name__)


def crawl_and_store() -> None:
    """Fetch posts, analyze them and store recommendations."""
    links = list(get_post_links(max_pages=MAX_PAGES))
    logger.info("Total collected: %s post links", len(links))

    curated = []  # ✅ Important: define before usage

    for page_num, idx, link in links:
        logger.info("Processing [%s/%s] %s", idx + 1, len(links), link)
        try:
            # Parse the blog post and extract relevant fields
            data = parse_post(link)

            # Skip entries with no textual content
            if not data.get("short_review") and not data.get("full_review"):
                logger.warning("Skipping: No review content found")
                continue

            reviewer = data.get("reviewer") or "Unknown"

            # Step 1: determine if this is in fact a movie review
            review_check = is_film_review(data["title"], data["short_review"])
            logger.debug("Review Check: %s", review_check)

            if not review_check.lower().startswith("yes"):
                logger.info("Skipping: Not a review post")
                continue
            
            # Step 2: Extract movie title with fallback
            try:
                movie_title = extract_movie_title(data['title'])
                if movie_title.lower() == "none":
                    movie_title = None
                logger.debug("Extracted movie title: %s", movie_title)
            except Exception as e:
                logger.error(
                    "Error extracting movie title from '%s': %s", data['title'], e
                )
                movie_title = None

            # Step 3: Sentiment analysis using LLM
            try:
                sentiment_raw = analyze_sentiment(
                    data["full_review"], data["short_review"]
                )
                sentiment = sentiment_raw.strip().split()[0]  # Get only Yes/No/Maybe
            except Exception as e:
                logger.error("Sentiment analysis failed: %s", e)
                sentiment = None

            logger.info(
                "RECOMMENDED: %s by %s | Movie: %s | Sentiment: %s",
                data["title"],
                reviewer,
                movie_title,
                sentiment,
            )
            logger.debug("Short Review: %s", data["short_review"])
            logger.debug("Full Review Excerpt: %s", data["full_review"])

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
                logger.info("Recommended: %s by %s", data["title"], reviewer)
        except Exception as e:
            logger.error("Error processing %s: %s", link, e)

def main():
    print("🎬 Starting Movie Review Miner...\n")
    crawl_and_store()


if __name__ == "__main__":
    main()
