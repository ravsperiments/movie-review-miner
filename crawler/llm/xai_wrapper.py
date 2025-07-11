"""
Wrapper for the XAI API (example generic provider).
"""
import os
import asyncio
import random

from dotenv import load_dotenv
import httpx
from xai_sdk import Client

from ..utils.logger import get_logger
from ..utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUESTS_IN_FLIGHT,
    LLM_PROMPT_LENGTH,
)


class XaiWrapper:
    """
    A wrapper for the XAI API (chat/completions style endpoint).
    """
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            get_logger(__name__).warning(
                "XAI_API_KEY not set. XAI wrapper will not be available."
            )
            self.client = None
        else:
            base_url = os.getenv("XAI_API_BASE_URL", "https://api.x.ai/v1")
            self.client = httpx.AsyncClient(
                base_url=base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        self.logger = get_logger(__name__)

    async def _handle_errors(self, api_call, *args, **kwargs):
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                resp = await api_call(*args, **kwargs)
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retries += 1
                    if retries == max_retries:
                        self.logger.error(f"Rate limit exceeded. Max retries reached. Giving up.")
                        raise

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
            except Exception as e:
                self.logger.error("XAI API call failed: %s", e)
                raise

    async def prompt_llm(self, prompt: str, model: str = "xai-default") -> str:
        """
        Generate a completion via the XAI API.

        Args:
            prompt: The prompt to send to the model.
            model: The XAI model name to use (defaults to 'xai-default').

        Returns:
            The raw text response from XAI.
        """
        if not self.client:
            raise RuntimeError("XAI client not initialized. Set XAI_API_KEY.")
        provider = "xai"
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(prompt))
        try:
            resp = await self._handle_errors(
                self.client.post,
                "/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                timeout=60.0,
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            self.logger.error("XAI generate_text failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()