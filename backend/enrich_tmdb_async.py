"""Link Supabase reviews to TMDb entries and update movie metadata."""

import asyncio
from db.review_queries import get_unenriched_links, update_review_with_movie_id
from db.movie_queries import get_movie_by_title, create_movie, update_movie_metadata
from llm.openai_wrapper import extract_movie_title
from tmdb.tmdb_api import search_tmdb  # abstract your TMDb API call here

async def enrich_reviews():
    """Populate movie_id and metadata for any unenriched reviews."""

    reviews = get_unenriched_links()
    print(f"🔍 Found {len(reviews)} reviews without movie linkage.")

    for review in reviews:
        try:
            title = extract_movie_title(review["blog_title"])
            if not title:
                print(f"❌ Skipping {review['id']} - no movie title extracted")
                continue

            movie = get_movie_by_title(title)
            if movie:
                movie_id = movie["id"]
            else:
                movie_id = create_movie(title)

            update_review_with_movie_id(review["id"], movie_id)

            metadata = await search_tmdb(title)
            if metadata:
                update_movie_metadata(movie_id, metadata)

            print(f"✅ Enriched review {review['id']} with movie {title}")
        except Exception as e:
            print(f"❌ Failed to enrich review {review.get('id', '?')}: {e}")

if __name__ == "__main__":
    asyncio.run(enrich_reviews())