#!/usr/bin/env python3

import asyncio
import json
import sys
from pathlib import Path
from pydantic import BaseModel
from pydantic_ai import Agent
from dotenv import load_dotenv

# Add parent directory to path to import prompts
sys.path.append(str(Path(__file__).parent.parent))

from llm.prompts.clean_review_system_prompt import CLEAN_REVIEW_SYSTEM_PROMPT
from llm.prompts.clean_review_user_prompt import CLEAN_REVIEW_USER_PROMPT_TEMPLATE

load_dotenv()

class CleanReviewOutput(BaseModel):
    cleaned_title: str
    cleaned_short_review: str

# Create the cleaning agent using the actual system prompt
agent = Agent(
    model='gpt-4o-mini',
    output_type=CleanReviewOutput,
    system_prompt=CLEAN_REVIEW_SYSTEM_PROMPT
)

async def main():
    # Load test data
    eval_data_path = Path(__file__).parent / "eval_data.json"
    with open(eval_data_path, 'r') as f:
        data = json.load(f)
    
    print("Running clean review evaluation...\n")
    
    for i, item in enumerate(data, 1):
        print(f"=== Case {i} ===")
        print(f"Original Title: {item['original_title']}")
        print(f"Original Review: {item['original_short_review'][:100]}...")
        
        # Clean with agent using the proper user prompt template
        prompt = CLEAN_REVIEW_USER_PROMPT_TEMPLATE.format(
            blog_title=item['original_title'],
            short_review=item['original_short_review'],
            full_review=item['original_short_review']  # Using short_review as fallback
        )
        
        try:
            result = await agent.run(prompt)
            cleaned = result.output
            
            print(f"Cleaned Title: {cleaned.cleaned_title}")
            print(f"Cleaned Review: {cleaned.cleaned_short_review[:100]}...")
            
            # Compare with expected if available
            if item.get('expected_cleaned_title'):
                print(f"Expected Title: {item['expected_cleaned_title']}")
                title_match = cleaned.cleaned_title.lower() in item['expected_cleaned_title'].lower() or item['expected_cleaned_title'].lower() in cleaned.cleaned_title.lower()
                print(f"Title Match: {'✓' if title_match else '✗'}")
            
            print("✓ Success")
            
        except Exception as e:
            print(f"✗ Error: {e}")
        
        print()

if __name__ == "__main__":
    asyncio.run(main())