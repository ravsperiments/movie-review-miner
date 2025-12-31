"""Pydantic models for LLM outputs."""
from pydantic import BaseModel, Field
from typing import Literal


class ProcessedReview(BaseModel):
    """Unified output for review processing - combines classification + cleaning."""

    is_film_review: bool = Field(
        description="True if this content is a film/movie review"
    )
    movie_names: list[str] = Field(
        default_factory=list,
        description="List of film titles mentioned in the review"
    )
    sentiment: Literal["Positive", "Negative", "Neutral"] = Field(
        description="Overall sentiment of the review"
    )
    cleaned_title: str = Field(
        description="Clean title without dates, 'Review:' prefix, or site names"
    )
    cleaned_short_review: str = Field(
        description="Concise summary of the review, max 280 characters"
    )
