"""Step 4: extract movie titles and link reviews to movies."""
from db.review_queries import get_unenriched_links, update_review_with_movie_id
from db.movie_queries import get_movie_by_title, create_movie
from llm.openai_wrapper import extract_movie_title
from utils.logger import get_logger
from tqdm import tqdm

logger = get_logger(__name__)

def link_movies() -> None:
    """Extract movie titles for reviews and link them to movie records."""
    reviews = get_unenriched_links()
    logger.info("Linking movies for %s reviews", len(reviews))

    for review in tqdm(reviews):
        try:
            title = extract_movie_title(review.get("blog_title", ""))
            if not title or title.lower() == "none":
                logger.info("No movie title found for review %s", review.get("id"))
                continue

            movie = get_movie_by_title(title)
            movie_id = movie["id"] if movie else create_movie(title)
            update_review_with_movie_id(review["id"], movie_id)
            logger.info("Linked review %s -> movie %s", review["id"], title)
        except Exception as e:
            logger.error("Movie link failed for %s: %s", review.get("id"), e)

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    link_movies()
