# backend/tasks/save_task.py

import uuid
import json
from pathlib import Path
from db.supabase_client import create_client
from utils.logger import get_logger
from datetime import datetime

# Optional: for Supabase DB insert
# from db.supabase import supabase

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%B %d, %Y").date()
    except Exception:
        return None  # fallback if parsing fails

# backend/tasks/save_task.py

def save_parsed_post(post_data: dict):
    import os
    from dotenv import load_dotenv
    from supabase import create_client

    # Load credentials (only once inside the worker)
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    supabase = create_client(supabase_url, supabase_key)

    logger = get_logger(__name__)
    logger.info("Saving to Supabase: %s", post_data.get('title', '')[:50])

    data = {
        "link": post_data["url"],
        "short_review": post_data.get("summary"),
        "full_excerpt": post_data.get("full_review"),
        "post_date": post_data.get("date")
    }

    try:
        response = supabase.table("test_reviews").insert(data).execute()
        logger.info("Inserted: %s", response)
    except Exception as e:
        logger.error("Failed to save post: %s", e)
        with open("failed_links.txt", "a") as f:
            f.write(f"[supabase_error] {post_data['url']} error: {e}\n")

