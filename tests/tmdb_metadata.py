# tmdb_metadata.py

import os
import requests

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"

def get_movie_metadata(movie_title):
    if not TMDB_API_KEY:
        raise ValueError("TMDB_API_KEY not set in environment.")

    search_url = f"{TMDB_API_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": movie_title,
        "language": "en-US"
    }

    try:
        res = requests.get(search_url, params=params)
        res.raise_for_status()
        data = res.json()
        results = data.get("results", [])

        if not results:
            return {}

        # Take the first search result
        movie = results[0]
        return {
            "tmdb_id": movie.get("id"),
            "release_year": movie.get("release_date", "")[:4],
            "language": movie.get("original_language"),
            "genre_ids": movie.get("genre_ids", []),
            "title": movie.get("title"),
        }
    except Exception as e:
        print(f"❌ TMDb metadata fetch failed for '{movie_title}': {e}")
        return {}
