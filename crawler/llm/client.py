"""Unified LLM client using Instructor for structured outputs."""
import os
import logging
from typing import TypeVar

import instructor
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Client cache
_clients: dict = {}


def get_client(provider: str):
    """Get or create instructor-patched client for provider."""
    if provider in _clients:
        return _clients[provider]

    if provider == "anthropic":
        _clients[provider] = instructor.from_anthropic(AsyncAnthropic())
    elif provider == "openai":
        _clients[provider] = instructor.from_openai(AsyncOpenAI())
    elif provider == "groq":
        _clients[provider] = instructor.from_openai(
            AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY"),
            )
        )
    elif provider == "ollama":
        _clients[provider] = instructor.from_openai(
            AsyncOpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",
            )
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return _clients[provider]


def parse_model_string(model: str) -> tuple[str, str]:
    """Parse 'provider/model' into (provider, model_name)."""
    if "/" in model:
        provider, model_name = model.split("/", 1)
    else:
        # Default to anthropic for unprefixed models
        provider, model_name = "anthropic", model
    return provider, model_name


async def process_with_llm(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    max_retries: int = 3,
) -> T:
    """
    Call any LLM with structured output.

    Args:
        model: Provider/model string (e.g., "anthropic/claude-3-5-sonnet-latest")
        system_prompt: System instructions
        user_prompt: User message with data
        response_model: Pydantic model for structured output
        max_retries: Retry attempts for validation errors

    Returns:
        Parsed Pydantic model instance
    """
    provider, model_name = parse_model_string(model)
    client = get_client(provider)

    logger.debug(f"Calling {provider}/{model_name}")

    if provider == "anthropic":
        return await client.messages.create(
            model=model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            response_model=response_model,
            max_retries=max_retries,
        )
    else:
        # OpenAI-compatible (OpenAI, Groq, Ollama)
        return await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=response_model,
            max_retries=max_retries,
        )
