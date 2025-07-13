"""Wrappers around the Mistral API used for classification tasks."""

import os
import asyncio
import random
from dotenv import load_dotenv
from mistralai.client import MistralClient
from mistralai.async_client import MistralAsyncClient
from mistralai.models.chat_completion import ChatMessage

from ..utils.logger import get_logger
from ..utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUESTS_IN_FLIGHT,
    LLM_PROMPT_LENGTH,
    LLM_PROMPT_TOKENS,
    LLM_COMPLETION_TOKENS,
    LLM_TOTAL_TOKENS,
)

class MistralWrapper:
    """
    A wrapper for the Mistral API, providing a standardized interface for prompting language models.
    """
    def __init__(self):
        """
        Initializes the MistralWrapper, loading the API key from environment variables and setting up the client.
        """
        load_dotenv()
        self.client = MistralAsyncClient(api_key=os.getenv("MISTRAL_API_KEY"))
        self.logger = get_logger(__name__)

    async def _handle_rate_limit(self, api_call, *args, **kwargs):
        """
        Handles rate limiting errors from the Mistral API with exponential backoff.

        Args:
            api_call: The API call to be executed.
            *args: Positional arguments for the API call.
            **kwargs: Keyword arguments for the API call.

        Returns:
            The result of the API call.
        """
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                return await api_call(*args, **kwargs)
            except Exception as e:
                if "rate limit" in str(e).lower():
                    retries += 1
                    if retries == max_retries:
                        self.logger.error(f"Rate limit exceeded. Max retries reached. Giving up.")
                        raise
                    
                    wait_time = backoff_time * (2 ** retries) + random.uniform(0, 1)
                    self.logger.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds.")
                    
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except Exception:
                raise

    async def prompt_llm(self, prompt: str, model: str = "mistral-small-latest") -> str:
        """
        Prompts a Mistral language model and returns the response.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use.

        Returns:
            The model's response as a string.
        """
        provider = 'mistral'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(prompt))
        try:
            api_call = self.client.chat
            response = await self._handle_rate_limit(
                api_call,
                model=model,
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.2,
            )
            
            if not response or not response.choices:
                self.logger.error("Invalid response from Mistral API: choices are missing.")
                return ""

            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error("Mistral generate_text failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
