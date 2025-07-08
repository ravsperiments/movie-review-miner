"""Wrappers around the OpenAI API used for classification tasks."""

import os
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from ..utils.logger import get_logger

class OpenAIWrapper:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger = get_logger(__name__)

    def generate_text(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            self.logger.error("OpenAI generate_text failed: %s", e)
            raise


    


