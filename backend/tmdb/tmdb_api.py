import os
import aiohttp
from utils.logger import get_logger
import json

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

logger = get_logger(__name__)

async def search_tmdb(title: str, year: str | None = None) -> dict | None:
    """Search TMDb for movie metadata by title, preferring matches by release year."""
    url = f"{TMDB_BASE_URL}/search/movie"
    params = {"query": title}
    if year:
        params["year"] = year  # Helps filter but doesn't guarantee

    headers = {
        "Authorization": f"Bearer {TMDB_API_KEY}",
        "Content-Type": "application/json;charset=utf-8",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.warning("TMDb API error %s: %s", response.status, await response.text())
                    return None

                data = await response.json()
                results = data.get("results", [])

                if not results:
                    logger.info("No TMDb results for title: %s", title)
                    return None

                # 🧠 Look for a result that matches the given year
                selected = None
                if year:
                    for result in results:
                        release_date = result.get("release_date", "")
                        if release_date.startswith(year):
                            selected = result
                            break

                # Fallback to top result
                if not selected:
                    selected = results[0]

                return {
                    "release_year": selected.get("release_date", "")[:4] or None,
                    "language": selected.get("original_language"),
                    "genre": ", ".join(str(genre_id) for genre_id in selected.get("genre_ids", [])),
                    "popularity": selected.get("popularity"),
                    "poster_path": selected.get("poster_path"),
                }

        except Exception as e:
            logger.error("Error during TMDb search for '%s': %s", title, e)
            return None
