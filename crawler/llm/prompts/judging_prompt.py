JUDGING_PROMPT_TEMPLATE = """
As an AI assistant, your task is to compare an original text with an edited version and provide a judgment.

Original Text:
{original_text}

Edited Text:
{edited_text}

Your judgment should focus on:
- Whether the edited text is an improvement over the original.
- Any significant changes or discrepancies.
- Overall quality and adherence to the implied intent of the original.

Provide your judgment in a JSON object with the following keys:
- "is_improvement": boolean (true if edited is an improvement, false otherwise)
- "reason": string (explanation for your judgment)
- "confidence": float (a score from 0.0 to 1.0 indicating your confidence in the judgment)

Example:
{
  "is_improvement": true,
  "reason": "The edited text is more concise and grammatically correct.",
  "confidence": 0.95
}
"""
