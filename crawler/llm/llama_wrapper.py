"""Wrapper for LLaMA models via the Ollama CLI."""

import os
import asyncio
from dotenv import load_dotenv

from ..utils.logger import get_logger


class LlamaWrapper:
    """Wrapper for LLaMA models via Ollama CLI."""

    def __init__(self):
        load_dotenv()
        self.default_model = os.getenv("LLAMA_MODEL_NAME", "phi3:mini")
        self.logger = get_logger(__name__)

    async def prompt_llm(self, prompt: str, model: str = None) -> str:
        """
        Generates text using the specified LLaMA model via the Ollama CLI.

        Args:
            prompt: The prompt to send to the model.
            model: Optional model name override; if omitted, uses LLAMA_MODEL_NAME.

        Returns:
            The text response from the model.
        """
        model_name = model or self.default_model
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama",
                "run",
                model_name,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode().strip()
                self.logger.error("Ollama run failed (model %s): %s", model_name, err)
                raise RuntimeError(f"Ollama run failed: {err}")
            return stdout.decode().strip()
        except Exception as e:
            self.logger.error("Ollama generate_text failed: %s", e)
            raise
