"""Step 5: run sentiment analysis on movie reviews."""
from crawler.db.review_queries import get_reviews_missing_sentiment, update_sentiment_for_review
from llm.openai_wrapper import analyze_sentiment
from crawler.utils.io_helpers import write_failure
from crawler.utils import StepLogger
from crawler.db.pipeline_logger import log_step_result
from tqdm import tqdm

def generate_sentiment() -> None:
    """Generate sentiment labels for reviews lacking them."""
    step_logger = StepLogger("step_5_generate_sentiment")
    reviews = get_reviews_missing_sentiment()
    step_logger.metrics["input_count"] = len(reviews)
    step_logger.logger.info("Generating sentiment for %s reviews", len(reviews))

    for review in tqdm(reviews):
        try:
            sentiment = analyze_sentiment(
                review.get("blog_title", ""),
                review.get("short_review", ""),
                review.get("full_excerpt", ""),
            )

            if not sentiment:
                step_logger.logger.warning(
                    "No sentiment returned for review %s", review["id"]
                )
                continue

            clean = sentiment.strip()
            if clean in {"Yes", "No", "Maybe"}:
                update_sentiment_for_review(review["id"], clean)
                step_logger.metrics["saved_count"] += 1
                step_logger.logger.info(
                    "Updated sentiment for %s -> %s", review["id"], sentiment
                )
                log_step_result(
                    "analyze_sentiment",
                    link_id=review.get("id"),
                    attempt_number=1,
                    status="success",
                    result_data={"sentiment": clean},
                )
            else:
                step_logger.logger.info(
                    "Skipping sentiment for %s -> %s", review["id"], sentiment
                )
        except Exception as e:
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.error(
                "Sentiment analysis failed for %s: %s", review.get("id"), e, exc_info=True
            )
            write_failure("failed_sentiment.txt", str(review.get("id")), e)
            log_step_result(
                "analyze_sentiment",
                link_id=review.get("id"),
                attempt_number=1,
                status="failure",
                error_message=str(e),
            )
        finally:
            step_logger.metrics["processed_count"] += 1
    step_logger.finalize()

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    generate_sentiment()
