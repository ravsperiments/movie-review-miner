## Tasks

### July 14, 2025

*   Refactored all LLM wrappers to use a standardized `prompt_llm` function that accepts `system_prompt` and `user_prompt` arguments.
*   Updated the `llm_controller.py` to handle the new `prompt_llm` function signature.
*   This change simplifies the process of adding new LLM providers and ensures a consistent interface across all wrappers.
