import os
from dotenv import load_dotenv
import google.generativeai as genai

from ..utils.logger import get_logger

class GeminiWrapper:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        self.logger = get_logger(__name__)

    def generate_text(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            self.logger.error("Gemini generate_text failed: %s", e)
            raise
