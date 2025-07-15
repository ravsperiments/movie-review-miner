"""Wrappers around the Groq API used for classification tasks."""

import os
import asyncio
import random
from dotenv import load_dotenv
from groq import Groq, AsyncGroq, GroqError
import logging

from ..utils.logger import get_logger
from ..utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUESTS_IN_FLIGHT,
    LLM_PROMPT_LENGTH,
    LLM_PROMPT_TOKENS,
    LLM_COMPLETION_TOKENS,
    LLM_TOTAL_TOKENS,
)

logger = logging.getLogger(__name__)

class GroqWrapper:
    def __init__(self):
        load_dotenv()
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.logger = get_logger(__name__)

    async def _handle_rate_limit(self, api_call, *args, **kwargs):
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                return await api_call(*args, **kwargs)
            except GroqError as e:
                if e.status_code == 429:
                    retries += 1
                    if retries == max_retries:
                        self.logger.error(f"Rate limit exceeded. Max retries reached. Giving up.")
                        raise

                    # Get retry-after header if available, otherwise use exponential backoff
                    retry_after = e.response.headers.get("retry-after")
                    if retry_after:
                        wait_time = int(retry_after)
                        self.logger.warning(f"Rate limit exceeded. Retrying in {wait_time} seconds.")
                    else:
                        wait_time = backoff_time * (2 ** retries) + random.uniform(0, 1)
                        self.logger.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds.")

                    await asyncio.sleep(wait_time)
                else:
                    raise
            except Exception:
                raise

    async def prompt_llm(self, system_prompt: str, user_prompt: str, model: str = "llama3-8b-8192") -> str:
        provider = 'groq'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(user_prompt))
        try:
            api_call = self.client.chat.completions.create
            response = await self._handle_rate_limit(
                api_call,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
            )

            if not response or not response.choices:
                self.logger.error("Invalid response from Groq API: choices are missing.")
                return ""
            response_text = response.choices[0].message.content
            return response_text.strip()
        except GroqError as e:
            self.logger.error("Groq generate_text failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
