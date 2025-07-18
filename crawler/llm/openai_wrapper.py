"""Wrappers around the OpenAI API used for classification tasks."""

import os
import asyncio
import random
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI, OpenAIError

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

class OpenAIWrapper:
    def __init__(self):
        load_dotenv()
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger = logging.getLogger(__name__)

    async def _handle_rate_limit(self, api_call, *args, **kwargs):
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                return await api_call(*args, **kwargs)
            except OpenAIError as e:
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

    async def prompt_llm(self, system_prompt: str, user_prompt: str, model: str = "gpt-3.5-turbo") -> str:
        provider = 'openai'
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
                self.logger.error("Invalid response from OpenAI API: choices are missing.")
                return ""

            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            self.logger.error("OpenAI generate_text failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
