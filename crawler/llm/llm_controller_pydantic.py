import os
import instructor
from typing import Type
from crawler.llm.gemini_wrapper import GeminiWrapper
from crawler.llm.schemas import LLMClassificationOutput
from crawler.utils.singleton import Singleton
from pydantic import BaseModel

class LLMControllerPydantic(metaclass=Singleton):
    """
    A controller for managing interactions with different LLM providers using Pydantic and instructor.
    This class is a Singleton to ensure a single point of control for LLM operations.
    """

    def __init__(self):
        """
        Initializes the LLMController, setting up wrappers for different LLM providers.
        """
        self.wrappers = {}

        # Initialize Gemini wrapper and patch with instructor
        try:
            gemini_wrapper = GeminiWrapper()
            self.wrappers["gemini"] = instructor.patch(gemini_wrapper.client, mode=instructor.Mode.JSON)
            self.wrappers["gemini-1.5-pro"] = self.wrappers["gemini"]
        except Exception as e:
            print(f"Could not initialize GeminiWrapper: {e}")

        if not self.wrappers:
            raise RuntimeError("No LLM wrappers could be initialized. Check API keys and environment variables.")

    async def prompt_llm(
        self, 
        model_name: str, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Generates content using the specified LLM model and returns a Pydantic object.

        Args:
            model_name: The name of the LLM model to use (e.g., "gemini-1.5-pro").
            system_prompt: The system prompt to guide the model.
            user_prompt: The user's prompt for text generation.
            response_model: The Pydantic model to structure the response.

        Returns:
            A Pydantic object representing the LLM's response.
        """

        wrapper = None
        if model_name.startswith("gemini"):
            wrapper = self.wrappers.get("gemini")
        
        if not wrapper:
            raise ValueError(f"No wrapper found for model: {model_name}")

        return await wrapper.generate_content(
            [user_prompt, system_prompt],
            response_model=response_model,
            model=model_name
        )
