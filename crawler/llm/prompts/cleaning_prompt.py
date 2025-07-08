CLEANING_PROMPT_TEMPLATE = """
As an AI assistant, your task is to clean up the provided text fields. 

Here's the data:
{text_fields}

Your goal is to:
- Correct any grammatical errors or typos.
- Ensure consistent formatting.
- Remove any irrelevant or redundant information.
- Standardize terminology where appropriate.

Provide the cleaned text fields in a JSON array format, where each element corresponds to the cleaned version of the input text field. For example: 
["cleaned text 1", "cleaned text 2"]
"""
