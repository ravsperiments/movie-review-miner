#!/usr/bin/env python3
"""
Evaluation script for clean review LLM output.

Runs clean review processing against test data and validates output quality.
Uses the unified Instructor-based LLM client with ProcessedReview schema.
"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import prompts
sys.path.append(str(Path(__file__).parent.parent))

from review_aggregator.llm.client import process_with_llm
from review_aggregator.llm.schemas import ProcessedReview

# Try to load prompts if available, otherwise use defaults
try:
    from llm.prompts.clean_review_system_prompt import CLEAN_REVIEW_SYSTEM_PROMPT
except ImportError:
    CLEAN_REVIEW_SYSTEM_PROMPT = """
### ROLE
You are an assistant to Baradwaj Rangan (BR), a noted film critic who primarily reviews Indian films. You are helping to clean and improve **his movie review titles and short summaries** for better presentation.

### TASK
Clean messy titles and short reviews by removing unwanted elements and generating meaningful content where needed.
"""

load_dotenv()


async def evaluate_clean_review(original_title: str, original_short_review: str, original_full_review: str) -> ProcessedReview:
    """
    Evaluate clean review processing on a single test case.

    Args:
        original_title: The original review title.
        original_short_review: The original short review text.
        original_full_review: The original full review text.

    Returns:
        ProcessedReview: The cleaned review output from the LLM.

    Raises:
        Exception: If LLM processing fails.
    """
    user_prompt = f"""
Please clean the following movie review data:
Title: {original_title}
Short Review: {original_short_review}
Full Review: {original_full_review}
"""

    result = await process_with_llm(
        model="anthropic/claude-3-5-sonnet-latest",
        system_prompt=CLEAN_REVIEW_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=ProcessedReview,
        max_retries=3
    )

    return result


async def main():
    """Run evaluation on all test cases from eval_data.json."""
    # Load test data
    eval_data_path = Path(__file__).parent / "eval_data.json"
    with open(eval_data_path, 'r') as f:
        data = json.load(f)

    print("Running clean review evaluation...\n")

    for i, item in enumerate(data, 1):
        print(f"=== Case {i} ===")
        print(f"Original Title: {item['original_title']}")
        print(f"Original Review: {item['original_short_review'][:100]}...")

        try:
            cleaned = await evaluate_clean_review(
                original_title=item['original_title'],
                original_short_review=item['original_short_review'],
                original_full_review=item.get('original_full_review', item['original_short_review'])
            )

            print(f"Cleaned Title: {cleaned.cleaned_title}")
            print(f"Cleaned Review: {cleaned.cleaned_short_review[:100]}...")

            # Compare with expected if available
            if item.get('expected_cleaned_title'):
                print(f"Expected Title: {item['expected_cleaned_title']}")
                title_match = (cleaned.cleaned_title.lower() in item['expected_cleaned_title'].lower() or
                               item['expected_cleaned_title'].lower() in cleaned.cleaned_title.lower())
                print(f"Title Match: {'✓' if title_match else '✗'}")

            print("✓ Success")

        except Exception as e:
            print(f"✗ Error: {e}")

        print()


if __name__ == "__main__":
    asyncio.run(main())