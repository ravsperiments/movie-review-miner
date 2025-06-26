"""Step 5: run sentiment analysis on movie reviews."""
from db.review_queries import get_reviews_missing_sentiment, update_sentiment_for_review
from llm.openai_wrapper import analyze_sentiment
from utils.logger import get_logger
from utils.io_helpers import write_failure
from tqdm import tqdm

logger = get_logger(__name__)

def generate_sentiment() -> None:
    """Generate sentiment labels for reviews lacking them."""
    reviews = get_reviews_missing_sentiment()
    logger.info("Generating sentiment for %s reviews", len(reviews))

    for review in tqdm(reviews):
        try:
            sentiment = analyze_sentiment(
                review.get("blog_title", ""),
                review.get("short_review", ""),
            )

            if not sentiment:
                logger.warning("No sentiment returned for review %s", review["id"])
                continue

            clean = sentiment.strip()
            if clean in {"Yes", "No", "Maybe"}:
                update_sentiment_for_review(review["id"], clean)
                logger.info("Updated sentiment for %s -> %s", review["id"], sentiment)
            else:
                logger.info(
                    "Skipping sentiment for %s -> %s", review["id"], sentiment
                )
        except Exception as e:
            logger.error(
                "Sentiment analysis failed for %s: %s", review.get("id"), e, exc_info=True
            )
            write_failure("failed_sentiment.txt", str(review.get("id")), e)
