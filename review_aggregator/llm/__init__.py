"""LLM module - unified client for structured outputs."""
from review_aggregator.llm.client import process_with_llm, parse_model_string, get_client
from review_aggregator.llm.schemas import ProcessedReview

__all__ = [
    "process_with_llm",
    "parse_model_string",
    "get_client",
    "ProcessedReview",
]
