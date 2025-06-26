"""Step 4: extract movie titles and link reviews to movies."""
from db.review_queries import get_links_without_movieid, update_review_with_movie_id
from db.movie_queries import get_movie_by_title, create_movie
from llm.openai_wrapper import extract_movie_title
from utils.logger import StepLogger
from utils.io_helpers import write_failure
from tqdm import tqdm

def link_movies() -> None:
    """Extract movie titles for reviews and link them to movie records."""
    slog = StepLogger("step_4_link_movies")
    reviews = get_links_without_movieid()
    slog.set_input_count(len(reviews))
    slog.logger.info("Linking movies for %s reviews", len(reviews))

    for review in tqdm(reviews):
        try:
            title = extract_movie_title(review.get("blog_title", ""))
            if not title or title.lower() == "none":
                slog.logger.info("No movie title found for review %s", review.get("id"))
                slog.processed()
                continue

            movie = get_movie_by_title(title)
            movie_id = movie["id"] if movie else create_movie(title)
            update_review_with_movie_id(review["id"], movie_id)
            slog.logger.info("Linked review %s -> movie %s", review["id"], title)
            slog.processed()
            slog.saved()
        except Exception as e:
            slog.logger.error(
                "Movie link failed for %s: %s", review.get("id"), e, exc_info=True
            )
            slog.processed()
            slog.failed()
            write_failure("failed_movie_linking.txt", str(review.get("id")), e)
    slog.finalize()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    link_movies()
