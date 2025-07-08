"""Step 3: Clean and enrich short reviews."""
from crawler.db.review_queries import get_reviews_for_short_review_cleanup, update_short_review
from crawler.db.pipeline_logger import log_step_result
from crawler.llm.openai_wrapper import summarize_review_excerpt, clean_short_review
from crawler.utils import StepLogger
from crawler.utils.io_helpers import write_failure
from tqdm import tqdm

def is_placeholder_review(short_review: str) -> bool:
    """Determines if a short review is likely a placeholder or null."""
    if not short_review or len(short_review.strip()) < 50:
        return True
    
    # Common placeholder patterns
    placeholders = [
        "written and directed by",
        "for more, subscribe to",
        "subscribe to galatta plus",
        "full review here",
        "read the full review",
        "click here to read more",
        "watch the full video",
        "check out the full review",
        "this review may contain spoilers",
        "comments written in third person such as reviwer says" # This is a valid part of a review, but if it's the *only* content, it's a placeholder
    ]

    for phrase in placeholders:
        if phrase in short_review.lower():
            # If the placeholder is the *only* significant content, it's a placeholder
            if len(short_review.strip()) < len(phrase) + 20: # Arbitrary threshold
                return True
            # Special case for "this review may contain spoilers" - if it's the only thing, it's a placeholder
            if phrase == "this review may contain spoilers" and len(short_review.strip()) < 60:
                return True
    
    return False

def clean_short_reviews() -> None:
    """Cleans short reviews and enriches them if they are placeholders."""
    step_logger = StepLogger("short_review_cleanup")
    reviews_to_process = get_reviews_for_short_review_cleanup()
    step_logger.metrics["input_count"] = len(reviews_to_process)
    step_logger.metrics["cleaned_count"] = 0
    step_logger.metrics["enriched_count"] = 0
    step_logger.metrics["skipped_count"] = 0
    step_logger.logger.info("Cleaning %s short reviews", len(reviews_to_process))

    for review in tqdm(reviews_to_process):
        step_logger.metrics["processed_count"] += 1
        review_id = review.get("id")
        current_short_review = review.get("short_review", "")
        full_excerpt = review.get("full_excerpt", "")

        try:
            if is_placeholder_review(current_short_review):
                step_logger.logger.info(
                    "Placeholder detected for review %s. Summarizing full excerpt.", review_id
                )
                if full_excerpt:
                    new_short_review = summarize_review_excerpt(full_excerpt)
                    update_short_review(review_id, new_short_review)
                    step_logger.metrics["enriched_count"] += 1
                    step_logger.logger.info(
                        "Enriched short review for %s: %s", review_id, new_short_review
                    )
                    log_step_result(
                        "short_review_cleanup",
                        link_id=review_id,
                        attempt_number=1,
                        status="success",
                        result_data={
                            "original_short_review": current_short_review,
                            "new_short_review": new_short_review,
                            "action": "enriched",
                        },
                    )
                else:
                    step_logger.logger.warning(
                        "No full_excerpt available for review %s with placeholder short_review.", review_id
                    )
                    step_logger.metrics["skipped_count"] += 1
                    log_step_result(
                        "short_review_cleanup",
                        link_id=review_id,
                        attempt_number=1,
                        status="skipped",
                        error_message="No full_excerpt to summarize",
                    )
            else:
                # If not a placeholder, clean noisy phrases
                cleaned_review = clean_short_review(current_short_review)
                if cleaned_review != current_short_review:
                    update_short_review(review_id, cleaned_review)
                    step_logger.metrics["cleaned_count"] += 1
                    step_logger.logger.info(
                        "Cleaned short review for %s: %s", review_id, cleaned_review
                    )
                    log_step_result(
                        "short_review_cleanup",
                        link_id=review_id,
                        attempt_number=1,
                        status="success",
                        result_data={
                            "original_short_review": current_short_review,
                            "new_short_review": cleaned_review,
                            "action": "cleaned",
                        },
                    )
                else:
                    step_logger.metrics["skipped_count"] += 1
                    step_logger.logger.info(
                        "Short review for %s is already clean.", review_id
                    )
                    log_step_result(
                        "short_review_cleanup",
                        link_id=review_id,
                        attempt_number=1,
                        status="success",
                        result_data={
                            "original_short_review": current_short_review,
                            "action": "skipped_clean",
                        },
                    )

        except Exception as e:
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.error(
                "Failed to clean/enrich short review for %s: %s", review_id, e, exc_info=True
            )
            write_failure("failed_short_review_cleanup.txt", str(review_id), e)
            log_step_result(
                "short_review_cleanup",
                link_id=review_id,
                attempt_number=1,
                status="failure",
                error_message=str(e),
            )
    step_logger.finalize()

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    clean_short_reviews()