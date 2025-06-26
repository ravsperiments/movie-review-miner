import json
from tqdm import tqdm
from db.supabase_client import supabase
from llm.openai_wrapper import is_film_review
from utils.logger import get_logger

logger = get_logger(__name__)

def get_reviews_without_flag():
    result = (
        supabase.table("reviews")
        .select("id", "blog_title", "short_review")
        .is_("is_film_review", "null")
        .execute()
    )
    return result.data if result.data else []

def update_is_review(review_id, value: bool):
    try:
        supabase.table("reviews").update({"is_film_review": value}).eq("id", review_id).execute()
    except Exception as e:
        logger.error(f"Failed to update is_film_review for {review_id}: {e}")

def main():
    reviews = get_reviews_without_flag()
    logger.info(f"🔍 Found {len(reviews)} reviews without is_film_review flag")

    for review in tqdm(reviews, desc="Updating is_film_review"):
        try:
            result = is_film_review(review["blog_title"], review["short_review"])
            update_is_review(review["id"], result)
        except Exception as e:
            logger.warning(f"⚠️ Error on review {review['id']}: {e}")

if __name__ == "__main__":
    main()
