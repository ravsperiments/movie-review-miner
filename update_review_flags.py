import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from crawl.db.review_queries import update_is_film_review

load_dotenv()

def run_update(review_id, value):
    print(f"Attempting to update review ID: {review_id} to is_film_review={value}")
    try:
        update_is_film_review(review_id, value)
        print(f"Successfully updated review ID: {review_id}")
    except Exception as e:
        print(f"Failed to update review ID: {review_id}. Error: {e}")
    print("-" * 30)

if __name__ == "__main__":
    review_ids_to_update = [
        "daf1562f-90c1-4fb2-a1e4-ab8d95a4d158",
        "cb0d2f3b-6e6f-402c-8bc7-db8852a67d15"
    ]

    for review_id in review_ids_to_update:
        run_update(review_id, True)
