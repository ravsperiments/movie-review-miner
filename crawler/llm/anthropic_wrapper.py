import os
import anthropic
import logging
import json
import traceback
import re
from anthropic import AsyncAnthropic
from anthropic import APIError, APIStatusError, APITimeoutError

logger = logging.getLogger(__name__)

from ..utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUESTS_IN_FLIGHT,
    LLM_PROMPT_LENGTH,
)

class AnthropicWrapper:
    """
    A wrapper for the Anthropic API (Claude models).
    """
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment variables. Anthropic models will not be available.")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)

    async def prompt_llm(self, prompt: str, model: str = "claude-sonnet-4-0") -> str:
        """
        Generates text using the Anthropic API.

        Args:
            prompt: The prompt for text generation.
            model: The specific Anthropic model to use (e.g., "claude-3-opus-20240229").

        Returns:
            The generated text.
        """
        if not self.client:
            raise RuntimeError("Anthropic client not initialized. ANTHROPIC_API_KEY is missing.")
        provider = 'anthropic'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(prompt))
        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text

            # Extract JSON part using regex
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_string = json_match.group(0)
                return json_string
            else:
                logger.error(f"No JSON object found in Anthropic response: {response_text}")
                return response_text # Return original text if no JSON found, let downstream handle error

        except Exception as e:
            logger.error(f"An error occurred in prompt_llm for model {model}: {type(e).__name__}: {e}. Traceback: {traceback.format_exc()}")
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
