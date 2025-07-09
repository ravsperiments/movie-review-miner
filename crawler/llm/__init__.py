import os
from . import ollama_wrapper, openai_wrapper, xai_wrapper

# Determine selected LLM model from environment or set via CLI
_SELECTED_MODEL = os.getenv("LLM_MODEL", "openai").lower()

def set_llm_model(model: str) -> None:
    """Set the LLM model to use for wrapper dispatch."""
    global _SELECTED_MODEL
    _SELECTED_MODEL = model.lower()

def _get_module():
    if _SELECTED_MODEL == "openai":
        return openai_wrapper
    if _SELECTED_MODEL == "ollama":
        return ollama_wrapper
    if _SELECTED_MODEL == "xai":
        return xai_wrapper
    raise ValueError(f"Unknown LLM model: {_SELECTED_MODEL}")

def is_film_review(title: str, short_review: str) -> bool:
    """Dispatch is_film_review to the selected LLM wrapper."""
    return _get_module().is_film_review(title, short_review)

def analyze_sentiment(title: str, subtext: str, fullreview: str) -> str:
    """Dispatch analyze_sentiment to the selected LLM wrapper."""
    return _get_module().analyze_sentiment(title, subtext, fullreview)

def extract_movie_title(post_title: str) -> str:
    """Dispatch extract_movie_title to the selected LLM wrapper."""
    return _get_module().extract_movie_title(post_title)
