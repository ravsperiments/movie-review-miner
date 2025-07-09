import os
from dotenv import load_dotenv
import google.generativeai as genai

from ..utils.logger import get_logger
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
        self.logger = get_logger(__name__)

    async def prompt_llm(self, prompt: str, model: str = "gemini-1.0-pro") -> str:
        provider = 'gemini'
        LLM_REQUEST_COUNT.labels(provider=provider).inc()
        LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).inc()
        LLM_PROMPT_LENGTH.labels(provider=provider).observe(len(prompt))
        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            if response.text:
                return response.text
            self.logger.warning("Gemini generate_content did not return text. Response: %s", response)
            raise ValueError("Gemini generate_content did not return text.")
        except Exception as e:
            self.logger.error("Gemini generate_content failed: %s", e)
            raise
        finally:
            LLM_REQUESTS_IN_FLIGHT.labels(provider=provider).dec()
