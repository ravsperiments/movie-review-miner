"""Step 3: classify parsed posts as film reviews."""
from crawler.db.review_queries import get_unclassified_reviews, update_is_film_review
from llm.openai_wrapper import is_film_review
from crawler.utils.io_helpers import write_failure
from crawler.utils import StepLogger
from crawler.db.pipeline_logger import log_step_result
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
            llm_response = is_film_review(
                review.get("blog_title", ""), review.get("short_review", "")
            )
            is_film_review_flag = llm_response.lower().startswith("yes")
            update_is_film_review(review["id"], is_film_review_flag)
            step_logger.metrics["saved_count"] += 1
            step_logger.logger.info(
                "Updated review %s -> %s", review["id"], is_film_review_flag
            )
            log_step_result(
                "classify_review",
                link_id=review.get("id"),
                attempt_number=1,
                status="success",
                result_data={
                    "is_film_review": is_film_review_flag,
                    "llm_raw_response": llm_response,
                },
            )
        except Exception as e:
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.error(
                "Failed classification for %s: %s", review.get("id"), e, exc_info=True
            )
            write_failure("failed_classifications.txt", str(review.get("id")), e)
            log_step_result(
                "classify_review",
                link_id=review.get("id"),
                attempt_number=1,
                status="failure",
                error_message=str(e),
            )
    step_logger.finalize()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    classify_reviews()
