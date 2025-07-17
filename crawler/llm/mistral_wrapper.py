import os
import asyncio
import random
from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.models import UserMessage

import logging

logging.basicConfig(level=logging.INFO)

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
        load_dotenv()
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        self.logger = logging.getLogger(__name__)

    async def _handle_rate_limit(self, api_call, *args, **kwargs):
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
                        self.logger.error("Rate limit exceeded. Max retries reached. Giving up.")
                        raise
                    wait_time = backoff_time * (2 ** retries) + random.uniform(0, 1)
                    self.logger.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds.")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def prompt_llm(self, system_prompt: str, user_prompt: str, model: str = "mistral-small-latest") -> str:
        provider = 'mistral'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(user_prompt))
        try:
            response = await self._handle_rate_limit(
                self.client.chat.complete_async,
                model=model,
                messages=[
                    UserMessage(role="system", content=system_prompt),
                    UserMessage(role="user", content=user_prompt)
                ],
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
