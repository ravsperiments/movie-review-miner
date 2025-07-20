
"""
Orchestrator for cleaning parsed review fields using an LLM.
"""

import asyncio
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from pydantic_ai import Agent

from crawler.db.stg_clean_review_queries import get_staged_reviews, update_cleaned_review_fields

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CleanedReview(BaseModel):
    """Pydantic model for the cleaned review data."""
    cleaned_title: str = Field(..., description="A concise and informative title for the movie review.")
    cleaned_short_review: str = Field(..., description="A brief, engaging summary of the movie review.")

async def clean_review_fields():
    """
    Main function to fetch staged reviews, clean them using an LLM, and print the results.
    """
    logger.info("Starting LLM cleaning of staged reviews...")
    load_dotenv()
    
    # Create a Pydantic AI agent with Gemini model
    agent = Agent(
        'gemini-1.5-flash',
        output_type=CleanedReview,
        system_prompt="""
### ROLE
You are an assistant to Baradwaj Rangan (BR), a noted film critic who primarily reviews Indian films. You are helping to clean and improve **his movie review titles and short summaries** for better presentation.

### TASK
Clean messy titles and short reviews by:

**STEP 1: Clean existing text**
Remove unwanted elements like:
- "You can read the rest of the review here:"
- "Copyright ©2025 GALATTA."
- "Spoilers ahead" / "The rest of this review may contain spoilers."
- "SPOILERS AHEAD"
- Trailer/video links: "You can watch the trailer / video review here:"
- Any copyright notices or boilerplate text

**STEP 2: Generate if insufficient**
If there's not enough meaningful text after cleaning, or if the cleaned text doesn't resemble a proper title/review, generate new content in Baradwaj Rangan's style and append "(auto-generated)" at the end.

### BR'S WRITING STYLE
BR is nuanced and balanced - he doesn't simply say "good" or "bad" but explains why and what could have been better.

**Title Examples:**
- "Anurag Basu's 'Metro… In Dino' is an interesting and ambitious experiment, but it stays at a distance and we end up feeling very little"
- "Sri Ganesh's '3BHK' (Siddharth, Sarathkumar) is a well-made drama that showcases the middle class by focusing on their one big dream"
- "Ram's 'Paranthu Po' is a beautiful, kind, funny road movie about the ups and downs of life"

**Short Review Examples:**
- "Metro… In Dino: The film is about a number of characters in a number of relationship conflicts. Some are treated seriously, some are treated comically, and there's definitely a vision – but there's no emotional connection."
- "3BHK: Shiva, Grace Antony, and Mithul Ryan play an urban family that, like the title says, learns to fly away. The sweet, gentle, musical feel of the film makes even the feel-bad moments of life seem like a feel-good experience."
- "Parandu Po: The readily identifiable story is about moving out of rented houses and buying a home. And despite the many issues faced by the family, the director ensures that the film is an easy, pleasant watch."

### MUST-FOLLOW RULES
1. **Always clean first** - Remove unwanted text before considering generation
2. **Preserve BR's voice** - If generating, match his nuanced, balanced tone
3. **Mark auto-generated content** - Add "(auto-generated)" only when you create new content
4. **Focus on substance** - Titles should hint at the film's quality/approach, short reviews should give plot + assessment
5. **Be specific** - Mention key actors, director, or notable elements when relevant
        """
    )
    
    staged_reviews = get_staged_reviews(limit=5)

    if not staged_reviews:
        logger.info("No staged reviews found to clean.")
        return

    logger.info(f"Found {len(staged_reviews)} staged reviews to clean.")

    for review in staged_reviews:
        user_prompt = f"""
        Please clean the following movie review data:
        Title: {review['raw_parsed_title']}
        Short Review: {review['raw_parsed_short_review']}
        Full Review: {review['raw_parsed_full_review']}
        """

        try:
            result = await agent.run(user_prompt)
            cleaned_data = result.output
            
            # Update the database with cleaned data
            success = update_cleaned_review_fields(
                raw_page_id=review['raw_page_id'],
                cleaned_title=cleaned_data.cleaned_title,
                cleaned_short_review=cleaned_data.cleaned_short_review
            )
            
            if success:
                logger.info(f"✅ Successfully processed and saved cleaned data for raw_page_id: {review['raw_page_id']}")
                print("Original Title:", review['raw_parsed_title'])
                print("Cleaned Title:", cleaned_data.cleaned_title)
                print("Original Short Review:", review['raw_parsed_short_review'])
                print("Cleaned Short Review:", cleaned_data.cleaned_short_review)
                print("-" * 20)
            else:
                logger.error(f"❌ Failed to save cleaned data for raw_page_id: {review['raw_page_id']}")

        except Exception as e:
            logger.error(f"Error cleaning review with raw_page_id {review['raw_page_id']}: {e}")


if __name__ == "__main__":
    asyncio.run(clean_review_fields())
