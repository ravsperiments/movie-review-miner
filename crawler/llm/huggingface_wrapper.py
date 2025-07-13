"""Wrappers around the Hugging Face API used for classification tasks."""

import os
import asyncio
import random
from dotenv import load_dotenv
from huggingface_hub import AsyncInferenceClient
from huggingface_hub.utils import HfHubHTTPError

from ..utils.logger import get_logger
from ..utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUESTS_IN_FLIGHT,
    LLM_PROMPT_LENGTH,
    LLM_PROMPT_TOKENS,
    LLM_COMPLETION_TOKENS,
    LLM_TOTAL_TOKENS,
)

class HuggingFaceWrapper:
    def __init__(self):
        load_dotenv()
        self.client = AsyncInferenceClient(token=os.getenv("HF_TOKEN"))
        self.logger = get_logger(__name__)

    async def _handle_rate_limit(self, api_call, *args, **kwargs):
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                return await api_call(*args, **kwargs)
            except HfHubHTTPError as e:
                if e.response.status_code == 429:
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

    async def prompt_llm(self, prompt: str, model: str = "mistralai/Mistral-7B-Instruct-v0.1") -> str:
        provider = 'huggingface'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(prompt))
        try:
            api_call = self.client.text_generation
            response = await self._handle_rate_limit(
                api_call,
                prompt=prompt,
                model=model,
                max_new_tokens=1000,
            )
            
            return response.strip()
        except HfHubHTTPError as e:
            self.logger.error("Hugging Face generate_text failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
