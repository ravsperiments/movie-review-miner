
import os
import json
from typing import Any, Dict, List
from crawler.llm.ollama_wrapper import OLlamaWrapper
from crawler.llm.openai_wrapper import OpenAIWrapper
from crawler.llm.gemini_wrapper import GeminiWrapper
from crawler.llm.anthropic_wrapper import AnthropicWrapper
from crawler.llm.xai_wrapper import XaiWrapper
from crawler.llm.groq_wrapper import GroqWrapper
from crawler.utils.singleton import Singleton
from crawler.llm.prompts.cleaning_prompt import CLEANING_PROMPT_TEMPLATE
from crawler.llm.prompts.judging_prompt import JUDGING_PROMPT_TEMPLATE
from crawler.llm.prompts.is_film_review_prompt import IS_FILM_REVIEW_PROMPT_TEMPLATE

class LLMController(metaclass=Singleton):
    """
    A controller for managing interactions with different LLM providers (e.g., OpenAI, Gemini, Anthropic).
    This class is a Singleton to ensure a single point of control for LLM operations.
    """

    def __init__(self):
        """
        Initializes the LLMController, setting up wrappers for different LLM providers.
        """
        self.wrappers = {}
        self.default_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4") # Default model for cleaning/judging

        # Initialize OpenAI wrapper
        try:
            self.wrappers["openai"] = OpenAIWrapper()
            self.wrappers["gpt-4"] = self.wrappers["openai"]
            self.wrappers["gpt-3.5-turbo"] = self.wrappers["openai"]
        except Exception as e:
            print(f"Could not initialize OpenAIWrapper: {e}")

        # Initialize Gemini wrapper
        try:
            self.wrappers["gemini"] = GeminiWrapper()
            self.wrappers["gemini-pro"] = self.wrappers["gemini"]
            self.wrappers["gemini-pro-vision"] = self.wrappers["gemini"]
        except Exception as e:
            print(f"Could not initialize GeminiWrapper: {e}")

        # Initialize Anthropic wrapper
        try:
            self.wrappers["anthropic"] = AnthropicWrapper()
            self.wrappers["claude-3-5-haiku-latest"] = self.wrappers["anthropic"]
            self.wrappers["claude-sonnet-4-0"] = self.wrappers["anthropic"]
            self.wrappers["claude-3-7-sonnet-latest"] = self.wrappers["anthropic"]
        except Exception as e:
            print(f"Could not initialize AnthropicWrapper: {e}")

        # Initialize LLaMA wrapper (Ollama CLI)
        try:
            self.wrappers["ollama"] = OLlamaWrapper()
            self.wrappers["gemma2:2b-instruct-q4_K_M"] = self.wrappers["ollama"]
        except Exception as e:
            print(f"Could not initialize OLlamaWrapper: {e}")

        # Initialize XAI wrapper
        try:
            self.wrappers["xai"] = XaiWrapper()
            self.wrappers["xai-default"] = self.wrappers["xai"]
        except Exception as e:
            print(f"Could not initialize XaiWrapper: {e}")
        
        # Initialize Groq wrapper
        try:
            self.wrappers["groq"] = GroqWrapper()
            self.wrappers["llama3-8b-8192"] = self.wrappers["groq"]
        except Exception as e:
            print(f"Could not initialize GroqWrapper: {e}")

        if not self.wrappers:
            raise RuntimeError("No LLM wrappers could be initialized. Check API keys and environment variables.")

    async def prompt_llm(self, model_name: str, prompt: str) -> Any:
        """
        Generates content using the specified LLM model.

        Args:
            model_name: The name of the LLM model to use (e.g., "gpt-4", "claude-3-opus-20240229").
            prompt: The prompt for text generation.

        Returns:
            The response from the LLM.
        """
        wrapper = None
        if model_name.startswith("gpt"):
            wrapper = self.wrappers.get("openai")
        elif model_name.startswith("gemini"):
            wrapper = self.wrappers.get("gemini")
        elif model_name.startswith("claude"):
            wrapper = self.wrappers.get("anthropic")
        elif model_name.startswith("phi"):
            wrapper = self.wrappers.get("ollama")
        elif model_name.startswith("grok"):
            wrapper = self.wrappers.get("xai")
        elif model_name.startswith("gemma2-9b"):
            wrapper = self.wrappers.get("groq")
        if not wrapper:
            raise ValueError(f"No wrapper found for model: {model_name}")

        return await wrapper.prompt_llm(prompt, model=model_name)

    async def run_cleaning(self, text_fields: List[str]) -> Dict[str, Any]:
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
                response = await self.prompt_llm(self.default_model, prompt)
                cleaned_texts = json.loads(response)
                return {"cleaned_texts": cleaned_texts}
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}. Retrying...")
            except Exception as e:
                print(f"Error during cleaning: {e}. Retrying...")
        return {"error": "Failed to clean texts after multiple retries."}

    async def run_judging(self, original: str, edited: str) -> Dict[str, Any]:
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
                response = await self.prompt_llm(self.default_model, prompt)
                judgment = json.loads(response)
                return {"judgment": judgment}
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}. Retrying...")
            except Exception as e:
                print(f"Error during judging: {e}. Retrying...")
        return {"error": "Failed to judge texts after multiple retries."}


