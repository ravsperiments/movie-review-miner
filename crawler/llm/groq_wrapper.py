"""Wrappers around the Groq API used for classification tasks."""

import os
from dotenv import load_dotenv
from groq import Groq, AsyncGroq, GroqError

from ..utils.logger import get_logger
from ..utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUESTS_IN_FLIGHT,
    LLM_PROMPT_LENGTH,
    LLM_PROMPT_TOKENS,
    LLM_COMPLETION_TOKENS,
    LLM_TOTAL_TOKENS,
)

class GroqWrapper:
    def __init__(self):
        load_dotenv()
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.logger = get_logger(__name__)

    async def prompt_llm(self, prompt: str, model: str = "llama3-8b-8192") -> str:
        provider = 'groq'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(prompt))
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except GroqError as e:
            self.logger.error("Groq generate_text failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
