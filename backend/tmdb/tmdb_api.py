import os
import aiohttp
from utils.logger import get_logger

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

logger = get_logger(__name__)

async def search_tmdb(title: str) -> dict | None:
    """Search TMDb for movie metadata by title using v3 API key."""
    url = f"{TMDB_BASE_URL}/search/movie"
    params = {"query": title}
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

                top_result = results[0]
                return {
                    "release_year": top_result.get("release_date", "")[:4] or None,
                    "language": top_result.get("original_language"),
                    "genre": ", ".join(str(genre_id) for genre_id in top_result.get("genre_ids", [])),
                }

        except Exception as e:
            logger.error("Error during TMDb search for '%s': %s", title, e)
            return None
