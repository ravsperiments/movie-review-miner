import os
from supabase import create_client
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_unenriched_reviews():
    response = (
        supabase
        .table("reviews")
        .select("id, movie_title")
        .execute()
    )
    return response.data


def search_tmdb(movie_title: str) -> dict | None:
    """Search TMDb for movie metadata by title using v4 Bearer token."""
    url = "https://api.themoviedb.org/3/search/movie"
    headers = {
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY')}",
        "Content-Type": "application/json;charset=utf-8"
    }
    params = {"query": movie_title}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"❌ Skipped {movie_title}: TMDb API error {response.status_code}: {response.text}")
        return None

    data = response.json()
    if not data.get("results"):
        print(f"❌ Skipped {movie_title}: No results found")
        return None

    top_result = data["results"][0]
    return {
        "release_year": top_result.get("release_date", "")[:4],
        "language": top_result.get("original_language", ""),
        "genre_ids": ", ".join([g["name"] for g in data.get("genres", [])])
    }

def update_metadata(record_id, metadata):
    update = {
        "release_year": metadata.get("release_date", "")[:4] or None,
        "language": metadata.get("original_language"),
        "genre": ", ".join(str(genre_id) for genre_id in metadata.get("genre_ids", []))
    }
    supabase.table("reviews").update(update).eq("id", record_id).execute()

def main():
    reviews = fetch_unenriched_reviews()
    print(f"🔍 Found {len(reviews)} unenriched reviews.")

    for review in reviews:
        try:
            print(f"🎞 Processing: {review['movie_title']}...")
            metadata = search_tmdb(review['movie_title'])
            print(metadata)
            update_metadata(review['id'], metadata)
            print("✅ Updated Supabase.")
        except Exception as e:
            print(f"❌ Skipped {review['movie_title']}: {e}")

if __name__ == "__main__":
    main()
