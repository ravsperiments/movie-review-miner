"""Step 3: classify parsed posts as film reviews."""
from db.review_queries import get_unclassified_reviews, update_is_film_review
from llm.openai_wrapper import is_film_review
from utils.io_helpers import write_failure
from utils import StepLogger
from tqdm import tqdm


def classify_reviews() -> None:
    """Classify stored reviews as film reviews or not."""
    step_logger = StepLogger("step_3_classify_reviews")
    reviews = get_unclassified_reviews()
    step_logger.metrics["input_count"] = len(reviews)
    step_logger.logger.info("Classifying %s reviews", len(reviews))

    for review in tqdm(reviews):
        step_logger.metrics["processed_count"] += 1
        try:
            result = is_film_review(
                review.get("blog_title", ""), review.get("short_review", "")
            )
            update_is_film_review(review["id"], bool(result))
            step_logger.metrics["saved_count"] += 1
            step_logger.logger.info("Updated review %s -> %s", review["id"], result)
        except Exception as e:
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.error(
                "Failed classification for %s: %s", review.get("id"), e, exc_info=True
            )
            write_failure("failed_classifications.txt", str(review.get("id")), e)
    step_logger.finalize()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    classify_reviews()
