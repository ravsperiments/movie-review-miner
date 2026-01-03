"""Pydantic models for LLM outputs."""
from pydantic import BaseModel, Field
from typing import Literal


class ProcessedReview(BaseModel):
    """Unified output for review processing - combines classification + cleaning.

    When is_film_review is False, other fields should be empty/null.
    """

    is_film_review: bool = Field(
        description="True if this content is a film/movie review"
    )

    # Fields below are only populated when is_film_review=True
    movie_names: list[str] = Field(
        default_factory=list,
        description="List of film titles mentioned in the review. Empty if is_film_review=False."
    )
    sentiment: Literal["Positive", "Negative", "Neutral"] | None = Field(
        default=None,
        description="Overall sentiment of the review. Null if is_film_review=False."
    )
    cleaned_title: str = Field(
        default="",
        description="Clean title without dates, 'Review:' prefix, or site names. Empty if is_film_review=False."
    )
    cleaned_short_review: str = Field(
        default="",
        description="Concise summary of the review, max 280 characters. Empty if is_film_review=False."
    )
