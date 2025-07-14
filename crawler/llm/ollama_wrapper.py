"""Wrapper for LLaMA models via the Ollama CLI."""

import os
import asyncio
import random
from dotenv import load_dotenv

from ..utils.logger import get_logger


class OLlamaWrapper:
    """Wrapper for OLLaMA models via Ollama CLI."""

    def __init__(self):
        load_dotenv()
        self.default_model = os.getenv("OLLAMA_MODEL_NAME", "gemma2:2b-instruct-q4_K_M")
        self.logger = get_logger(__name__)

    async def _handle_errors(self, api_call, *args, **kwargs):
        retries = 0
        max_retries = 5
        backoff_time = 1
        while retries < max_retries:
            try:
                return await api_call(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries == max_retries:
                    self.logger.error(f"API call failed after {max_retries} retries. Giving up.")
                    raise
                
                wait_time = backoff_time * (2 ** retries) + random.uniform(0, 1)
                self.logger.warning(f"API call failed. Retrying in {wait_time:.2f} seconds.")
                await asyncio.sleep(wait_time)

    async def prompt_llm(self, system_prompt: str, user_prompt: str, model: str = None) -> str:
        """
        Generates text using the specified OLLaMA model via the Ollama CLI.

        Args:
            system_prompt: The system prompt to guide the model.
            user_prompt: The user's prompt for text generation.
            model: Optional model name override; if omitted, uses OLLAMA_MODEL_NAME.

        Returns:
            The text response from the model.
        """
        model_name = model or self.default_model
        
        # Combine system and user prompts for Ollama
        full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"

        async def ollama_run():
            proc = await asyncio.create_subprocess_exec(
                "ollama",
                "run",
                model_name,
                full_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode().strip()
                self.logger.error("Ollama run failed (model %s): %s", model_name, err)
                raise RuntimeError(f"Ollama run failed: {err}")
            return stdout.decode().strip()

        try:
            return await self._handle_errors(ollama_run)
        except Exception as e:
            self.logger.error("Ollama generate_text failed: %s", e)
            raise
