"""Step 3: classify parsed posts as film reviews."""
from db.review_queries import get_unclassified_reviews, update_is_film_review
from llm.openai_wrapper import is_film_review
from utils.logger import StepLogger
from utils.io_helpers import write_failure
from tqdm import tqdm

def classify_reviews() -> None:
    """Classify stored reviews as film reviews or not."""
    slog = StepLogger("step_3_classify_reviews")
    reviews = get_unclassified_reviews()
    slog.set_input_count(len(reviews))
    slog.logger.info("Classifying %s reviews", len(reviews))

    for review in tqdm(reviews):
        try:
            result = is_film_review(
                review.get("blog_title", ""), review.get("short_review", "")
            )
            update_is_film_review(review["id"], bool(result))
            slog.logger.info("Updated review %s -> %s", review["id"], result)
            slog.processed()
            slog.saved()
        except Exception as e:
            slog.logger.error(
                "Failed classification for %s: %s", review.get("id"), e, exc_info=True
            )
            slog.processed()
            slog.failed()
            write_failure("failed_classifications.txt", str(review.get("id")), e)
    slog.finalize()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    classify_reviews()
