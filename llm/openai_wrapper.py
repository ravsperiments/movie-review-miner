import os
from dotenv import load_dotenv
from openai import OpenAI
from openai.error import OpenAIError

from utils.logger import get_logger

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = get_logger(__name__)


def is_film_review(title: str, short_review: str) -> str:
    """Return 'Yes' or 'No' along with a short explanation."""
    prompt = f'''
You are a classifier that determines whether a blog post is a film review.

Rules:
- If the title contains phrases like "Readers Write In", "Readers Write", or similar, it is *not* a film review.
- Otherwise, if the title and snippet suggest the post is about the plot, direction, performances, or overall quality of a specific movie, it *is* a review.
- If unclear or off-topic, mark it as *not* a review.

Respond with "Yes" or "No", followed by a one-line reason.

Title:
"""{title}"""

Short Review Snippet:
"""{short_review}"""
'''

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        logger.debug("is_film_review response: %s", response)
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error("OpenAI is_film_review failed: %s", e)
        raise


def analyze_sentiment(title: str, subtext: str) -> str:
    """Return whether the reviewer recommends the movie as Yes, No or Maybe."""
    prompt = f'''
You are a sentiment analyzer tuned to the writing style of film critic Baradwaj Rangan (BR).
Classify the review as one of: "Yes", "No", or "Maybe" based on how the movie is ultimately portrayed.

Guidelines:
- Respond "Yes" if the review has no significant negative remarks or ends with an overall positive impression.
- Respond "No" if the review includes strong negative critique that outweighs any praise.
- Respond "Maybe" if the review is balanced, equivocating, or mildly critical but suggests it's still watchable.
- If the snippet does not appear to be a movie review at all, reply with "No – not a review".

Only respond with one of: Yes, No, Maybe, or No – not a review.

Below are the post title and a short excerpt from the review:

Title:
"""{title}"""

Subtext:
"""{subtext}"""
'''

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        logger.debug("analyze_sentiment response: %s", response)
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error("OpenAI analyze_sentiment failed: %s", e)
        raise

