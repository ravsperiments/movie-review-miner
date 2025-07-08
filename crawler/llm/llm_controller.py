
import os
import json
from typing import Any, Dict, List
from crawler.llm.llama_wrapper import LlamaWrapper
from crawler.llm.openai_wrapper import OpenAIWrapper
from crawler.llm.gemini_wrapper import GeminiWrapper
from crawler.utils.singleton import Singleton
from crawler.llm.prompts.cleaning_prompt import CLEANING_PROMPT_TEMPLATE
from crawler.llm.prompts.judging_prompt import JUDGING_PROMPT_TEMPLATE

class LLMController(metaclass=Singleton):
    """
    A controller for managing interactions with different LLM providers (e.g., OpenAI, Llama).
    This class is a Singleton to ensure a single point of control for LLM operations.
    """

    def __init__(self):
        """
        Initializes the LLMController, loading the appropriate LLM wrapper based on configuration.
        """
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai")
        if self.llm_provider == "llama":
            self.llm_wrapper = LlamaWrapper()
        elif self.llm_provider == "gemini":
            self.llm_wrapper = GeminiWrapper()
        else:
            self.llm_wrapper = OpenAIWrapper()

    def run_cleaning(self, text_fields: List[str]) -> Dict[str, Any]:
        """
        Runs a cleaning task on a list of text fields using the configured LLM.

        Args:
            text_fields: A list of strings to be cleaned.

        Returns:
            A dictionary containing the cleaned text fields.
        """
        prompt = CLEANING_PROMPT_TEMPLATE.format(text_fields=json.dumps(text_fields))
        retries = 3
        for i in range(retries):
            try:
                response = self.llm_wrapper.generate_text(prompt)
                cleaned_texts = json.loads(response)
                return {"cleaned_texts": cleaned_texts}
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}. Retrying...")
            except Exception as e:
                print(f"Error during cleaning: {e}. Retrying...")
        return {"error": "Failed to clean texts after multiple retries."}

    def run_judging(self, original: str, edited: str) -> Dict[str, Any]:
        """
        Runs a judging task to compare an original and edited text using the configured LLM.

        Args:
            original: The original text.
            edited: The edited text.

        Returns:
            A dictionary containing the judgment result.
        """
        prompt = JUDGING_PROMPT_TEMPLATE.format(original_text=original, edited_text=edited)
        retries = 3
        for i in range(retries):
            try:
                response = self.llm_wrapper.generate_text(prompt)
                judgment = json.loads(response)
                return {"judgment": judgment}
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}. Retrying...")
            except Exception as e:
                print(f"Error during judging: {e}. Retrying...")
        return {"error": "Failed to judge texts after multiple retries."}

    def switch_model(self, llm_provider: str):
        """
        Switches the LLM provider and re-initializes the wrapper.

        Args:
            llm_provider: The new LLM provider to use ("openai" or "llama").
        """
        self.llm_provider = llm_provider
        if self.llm_provider == "llama":
            self.llm_wrapper = LlamaWrapper()
        elif self.llm_provider == "gemini":
            self.llm_wrapper = GeminiWrapper()
        else:
            self.llm_wrapper = OpenAIWrapper()

