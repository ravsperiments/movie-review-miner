import os
import anthropic
import logging
import json
import traceback
import re
import asyncio
import random
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

    async def _handle_rate_limit(self, api_call, *args, **kwargs):
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                return await api_call(*args, **kwargs)
            except APIStatusError as e:
                if e.status_code == 429:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Rate limit exceeded. Max retries reached. Giving up.")
                        raise
                    
                    # Get retry-after header if available, otherwise use exponential backoff
                    retry_after = e.response.headers.get("retry-after")
                    if retry_after:
                        wait_time = int(retry_after)
                        logger.warning(f"Rate limit exceeded. Retrying in {wait_time} seconds.")
                    else:
                        wait_time = backoff_time * (2 ** retries) + random.uniform(0, 1)
                        logger.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds.")
                    
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except Exception:
                raise

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
            api_call = self.client.messages.create
            message = await self._handle_rate_limit(
                api_call,
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            
            if not message or not message.content:
                logger.error("Invalid response from Anthropic API: message or content is missing.")
                return "" # Return empty string if response is invalid

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
