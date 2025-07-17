import os
import asyncio
import random
from dotenv import load_dotenv
import google.generativeai as genai

import logging

logging.basicConfig(level=logging.INFO)

from ..utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUESTS_IN_FLIGHT,
    LLM_PROMPT_LENGTH,
)

class GeminiWrapper:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.logger = logging.getLogger(__name__)

    async def _handle_errors(self, api_call, *args, **kwargs):
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                return api_call(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries == max_retries:
                    self.logger.error(f"API call failed after {max_retries} retries. Giving up.")
                    raise

                wait_time = backoff_time * (2 ** retries) + random.uniform(0, 1)
                self.logger.warning(f"API call failed. Retrying in {wait_time:.2f} seconds.")
                await asyncio.sleep(wait_time)

    async def prompt_llm(self, system_prompt: str, user_prompt: str, model: str = "gemini-1.5-flash-latest") -> str:
        provider = 'gemini'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(user_prompt))
        try:
            model_instance = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt
            )
            response = await self._handle_errors(model_instance.generate_content, user_prompt)
            if response and response.text:
                return response.text
            self.logger.warning("Gemini generate_content did not return text. Response: %s", response)
            raise ValueError("Gemini generate_content did not return text.")
        except Exception as e:
            self.logger.error("Gemini generate_content failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
