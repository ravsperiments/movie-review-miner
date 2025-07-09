import os
import anthropic
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

class AnthropicWrapper:
    """
    A wrapper for the Anthropic API (Claude models).
    """
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment variables. Anthropic models will not be available.")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)

    async def prompt_llm(self, prompt: str, model: str = "claude-sonnet-4-0") -> str:
        """
        Generates text using the Anthropic API.

        Args:
            prompt: The prompt for text generation.
            model: The specific Anthropic model to use (e.g., "claude-3-opus-20240229").

        Returns:
            The generated text.
        """
        if not self.client:
            raise RuntimeError("Anthropic client not initialized. ANTHROPIC_API_KEY is missing.")

        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Error generating text with Anthropic model {model}: {e}")
            raise
