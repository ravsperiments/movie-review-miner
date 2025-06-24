import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Load Bearer token from .env
bearer_token = os.getenv("TMDB_API_KEY")
headers = {
    "Authorization": f"Bearer {bearer_token}"
}

# Example: Get movie details
response = requests.get("https://api.themoviedb.org/3/movie/11", headers=headers)
print("🎬 Movie Info:", response.json())
