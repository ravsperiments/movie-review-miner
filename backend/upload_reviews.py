import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()  # Optional: if you're using a .env file

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

with open("parsed_blog_posts.json", "r") as f:
    posts = json.load(f)

inserted = 0
for post in posts:
    data = {
        "link": post["url"],
        "blog_title": post["title"],
        "short_review": post["summary"],
        "post_date": post["date"],
        "full_excerpt": post["full_review"]
    }
    # Avoid duplicates based on URL
    existing = supabase.table("reviews").select("id").eq("link", post["url"]).execute()
    if existing.data:
        continue  # Skip if already exists

    response = supabase.table("reviews").insert(data).execute()
    inserted += 1

print(f"✅ Uploaded {inserted} new reviews to Supabase.")
