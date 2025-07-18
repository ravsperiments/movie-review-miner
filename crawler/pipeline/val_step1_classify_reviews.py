"""Step 3: classify parsed posts as film reviews."""
from crawler.db.scraper_queries import get_parsed_pages
from crawler.llm import is_film_review
from crawler.utils.io_helpers import write_failure
from crawler.utils import StepLogger
from crawler.db.pipeline_logger import log_step_result


def classify_reviews() -> None:
    """Classify stored reviews as film reviews or not."""
    step_logger = StepLogger("step_3_classify_reviews")
    parsed_pages = get_parsed_pages()
    step_logger.metrics["input_count"] = len(parsed_pages)
    step_logger.logger.info("Classifying %s reviews", len(parsed_pages))

    for page in parsed_pages:
        step_logger.metrics["processed_count"] += 1
        try:
            llm_response = is_film_review(
                page.get("blog_title", ""), page.get("short_review", "")
            )
            is_film_review_flag = llm_response
            #update_is_film_review(review["id"], is_film_review_flag)
            step_logger.metrics["saved_count"] += 1
            step_logger.logger.info(
                "Updated review %s -> %s", page["id"], is_film_review_flag
            )
            log_step_result(
                "classify_review",
                link_id=page.get("id"),
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
                "Failed classification for %s: %s", page.get("id"), e, exc_info=True
            )
            write_failure("failed_classifications.txt", str(page.get("id")), e)
            log_step_result(
                "classify_review",
                link_id=page.get("id"),
                attempt_number=1,
                status="failure",
                error_message=str(e),
            )
    step_logger.finalize()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    classify_reviews()
