"""Step 5: run sentiment analysis on movie reviews."""
from db.review_queries import get_reviews_missing_sentiment, update_sentiment_for_review
from llm.openai_wrapper import analyze_sentiment
from utils.logger import StepLogger
from utils.io_helpers import write_failure
from tqdm import tqdm

def generate_sentiment() -> None:
    """Generate sentiment labels for reviews lacking them."""
    slog = StepLogger("step_5_generate_sentiment")
    reviews = get_reviews_missing_sentiment()
    slog.set_input_count(len(reviews))
    slog.logger.info("Generating sentiment for %s reviews", len(reviews))

    for review in tqdm(reviews):
        try:
            sentiment = analyze_sentiment(
                review.get("blog_title", ""),
                review.get("short_review", ""),
                review.get("full_excerpt", ""),
            )

            if not sentiment:
                slog.logger.warning("No sentiment returned for review %s", review["id"])
                slog.processed()
                continue

            clean = sentiment.strip()
            if clean in {"Yes", "No", "Maybe"}:
                update_sentiment_for_review(review["id"], clean)
                slog.logger.info("Updated sentiment for %s -> %s", review["id"], sentiment)
                slog.processed()
                slog.saved()
            else:
                slog.logger.info(
                    "Skipping sentiment for %s -> %s", review["id"], sentiment
                )
                slog.processed()
        except Exception as e:
            slog.logger.error(
                "Sentiment analysis failed for %s: %s", review.get("id"), e, exc_info=True
            )
            slog.processed()
            slog.failed()
            write_failure("failed_sentiment.txt", str(review.get("id")), e)
    slog.finalize()

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    generate_sentiment()
