"""Unified LLM client using Instructor for structured outputs."""
import asyncio
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
# Gemini model cache (separate because it needs GenerativeModel instances)
_gemini_models: dict = {}


def get_client(provider: str, model_name: str = None):
    """Get or create instructor-patched client for provider.

    Args:
        provider: The LLM provider (anthropic, openai, groq, ollama, google)
        model_name: Required for google/gemini to create the right model instance
    """
    # For Gemini, we need a client per model
    if provider == "google":
        cache_key = f"google/{model_name}" if model_name else "google"
        if cache_key in _clients:
            return _clients[cache_key]

        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        # Create GenerativeModel and wrap with instructor
        gemini_model = genai.GenerativeModel(model_name=model_name or "gemini-1.5-pro")
        _clients[cache_key] = instructor.from_gemini(
            client=gemini_model,
            mode=instructor.Mode.GEMINI_JSON,
        )
        return _clients[cache_key]

    # Other providers use a single client
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
    max_retries: int = 1,
    timeout: float = 30.0,
) -> T:
    """
    Call any LLM with structured output.

    Args:
        model: Provider/model string (e.g., "anthropic/claude-sonnet-4-20250514")
        system_prompt: System instructions
        user_prompt: User message with data
        response_model: Pydantic model for structured output
        max_retries: Retry attempts for validation errors

    Returns:
        Parsed Pydantic model instance
    """
    provider, model_name = parse_model_string(model)
    client = get_client(provider, model_name)

    logger.debug(f"Calling {provider}/{model_name}")

    async def _call():
        if provider == "anthropic":
            return await client.messages.create(
                model=model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                response_model=response_model,
                max_retries=max_retries,
            )
        elif provider == "google":
            # Gemini uses generate_content with combined prompt
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            # Gemini client is sync, run in thread
            return await asyncio.to_thread(
                client.messages.create,
                messages=[{"role": "user", "content": combined_prompt}],
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

    return await asyncio.wait_for(_call(), timeout=timeout)
