"""Step 4: extract movie titles and link reviews to movies."""
from crawler.db.review_queries import get_links_without_movieid, update_review_with_movie_id
from crawler.db.movie_queries import get_movie_by_title, create_movie
from crawler.llm import extract_movie_title
from crawler.utils.io_helpers import write_failure
from crawler.utils import StepLogger
from crawler.db.pipeline_logger import log_step_result
from tqdm import tqdm

def link_movies() -> None:
    """Extract movie titles for reviews and link them to movie records."""
    step_logger = StepLogger("step_4_link_movies")
    reviews = get_links_without_movieid()
    step_logger.metrics["input_count"] = len(reviews)
    step_logger.logger.info("Linking movies for %s reviews", len(reviews))

    for review in tqdm(reviews):
        try:
            title = extract_movie_title(review.get("blog_title", ""))
            if not title or title.lower() == "none":
                step_logger.logger.info(
                    "No movie title found for review %s", review.get("id")
                )
                continue

            movie = get_movie_by_title(title)
            movie_id = movie["id"] if movie else create_movie(title)
            update_review_with_movie_id(review["id"], movie_id)
            step_logger.metrics["saved_count"] += 1
            step_logger.logger.info(
                "Linked review %s -> movie %s", review["id"], title
            )
            log_step_result(
                "link_movie",
                link_id=review.get("id"),
                movie_id=movie_id,
                attempt_number=1,
                status="success",
            )
        except Exception as e:
            step_logger.metrics["failed_count"] += 1
            step_logger.logger.error(
                "Movie link failed for %s: %s", review.get("id"), e, exc_info=True
            )
            write_failure("failed_movie_linking.txt", str(review.get("id")), e)
            log_step_result(
                "link_movie",
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
    link_movies()
