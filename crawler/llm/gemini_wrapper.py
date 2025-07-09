import os
from dotenv import load_dotenv
import google.generativeai as genai

from ..utils.logger import get_logger

class GeminiWrapper:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.logger = get_logger(__name__)

    async def prompt_llm(self, prompt: str, model: str = "gemini-1.0-pro") -> str:
        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            if response.text:
                return response.text
            else:
                self.logger.warning("Gemini generate_content did not return text. Response: %s", response)
                raise ValueError("Gemini generate_content did not return text.")
        except Exception as e:
            self.logger.error("Gemini generate_content failed: %s", e)
            raise
