from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class LLMClassificationOutput(BaseModel):
    is_film_review: Literal["Yes", "No", "Maybe"] = Field(..., description="Indicates if the text is a film review.")
    film_names: Optional[List[str]] = Field(None, description="A list of film titles mentioned in the text.")
    sentiment: Optional[Literal["Positive", "Negative", "Neutral"]] = Field(None, description="The inferred sentiment of the review.")
