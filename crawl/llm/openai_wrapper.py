"""Wrappers around the OpenAI API used for classification tasks."""

import os
from dotenv import load_dotenv
from openai import OpenAI
from openai import OpenAIError

from ..utils.logger import get_logger

# Load API credentials from .env and create the OpenAI client
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Shared logger for all API interactions
logger = get_logger(__name__)


def is_film_review(title: str, short_review: str) -> str:
    """Determine whether the given post is a movie review.

    Args:
        title: Post title extracted from the blog.
        short_review: The first paragraph or blurb of the post.

    Returns:
        Response text from the model beginning with ``Yes`` or ``No``.
    """
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
        # Send prompt to OpenAI's chat completion API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        #logger.debug("is_film_review response: %s", response)
        return response.choices[0].message.content.strip().lower().startswith("yes")
    except OpenAIError as e:
        # Surface any API errors to the caller
        logger.error("OpenAI is_film_review failed: %s", e)
        raise


def analyze_sentiment(title: str, subtext: str, fullreview: str) -> str:
    """Classify the sentiment of a review as Yes, No or Maybe.

    Args:
        title: Post title to provide context to the model.
        subtext: Excerpt from the review body.

    Returns:
        A string starting with ``Yes``, ``No`` or ``Maybe`` depending on
        the reviewer's stance.
    """
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

Full Review:
"""{fullreview}"""
'''

    try:
        # Ask the model to analyse sentiment of the provided text
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        #logger.debug("analyze_sentiment response: %s", response)
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error("OpenAI analyze_sentiment failed: %s", e)
        raise


def extract_movie_title(post_title: str) -> str:
    """Extract the name of the movie being reviewed, if any."""
    prompt = f'''
You are an assistant that extracts movie titles from blog post headlines on the film blog baradwajrangan.wordpress.com.

Given the following blog post title:
"""{post_title}"""

Return ONLY the name of the movie being reviewed. Do not include the director or actor names, and do not include quotes or additional commentary. If no movie title is present, return "None".
'''

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        #logger.debug("extract_movie_title response: %s", response)
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error("OpenAI extract_movie_title failed: %s", e)
        raise


