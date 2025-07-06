"""Async CRUD helpers for Supabase."""

from __future__ import annotations

from typing import Any

from .supabase_client import supabase
from utils.logger import get_logger

logger = get_logger(__name__)


async def upsert_review(review: dict[str, Any]) -> None:
    """Insert or update a review row."""
    try:
        supabase.table("reviews").upsert(review, on_conflict="link").execute()
    except Exception as e:
        logger.error("Failed to upsert review: %s", e)
        raise


async def get_or_create_movie(title: str) -> str:
    """Return movie id for title, creating the movie if needed."""
    try:
        res = supabase.table("movies").select("id").eq("title", title).limit(1).execute()
        if res.data:
            return res.data[0]["id"]
        insert = supabase.table("movies").insert({"title": title}).execute()
        return insert.data[0]["id"]
    except Exception as e:
        logger.error("get_or_create_movie failed for '%s': %s", title, e)
        raise


async def update_review_sentiment(review_id: str, sentiment: str) -> None:
    try:
        supabase.table("reviews").update({"sentiment": sentiment}).eq("id", review_id).execute()
    except Exception as e:
        logger.error("Failed to update sentiment for %s: %s", review_id, e)
        raise


async def update_movie_metadata(movie_id: str, data: dict[str, Any]) -> None:
    try:
        supabase.table("movies").update(data).eq("id", movie_id).execute()
    except Exception as e:
        logger.error("Failed to update movie metadata for %s: %s", movie_id, e)
        raise
