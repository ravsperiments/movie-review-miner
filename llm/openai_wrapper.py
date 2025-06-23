import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_sentiment(review_excerpt: str) -> str:
    """
    Uses OpenAI Chat API to determine if the reviewer recommends the movie.
    """
    prompt = f"""
Here is a short excerpt from a film review:

\"\"\"\n{review_excerpt}\n\"\"\"

Based on this, does the reviewer recommend the movie? Reply only with:
Yes or No, and a 1-line explanation.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def is_film_review(title: str, short_review: str) -> str:
    """
    Uses GPT to decide if this blog post looks like a film review.
    Returns: 'Yes – ...' or 'No – ...'
    """
    prompt = f"""
Given the following blog post metadata:

Title:
\"\"\"{title}\"\"\"

Short Review Snippet:
\"\"\"{short_review}\"\"\"

Does this appear to be a film review?
Reply with Yes or No, followed by a one-line reason.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()

def analyze_sentiment(review_excerpt: str) -> str:
    """
    Uses GPT to determine if the reviewer recommends the movie.
    Returns: 'Yes – ...' or 'No – ...'
    """
    prompt = f"""
Here is a short excerpt from a film review:

\"\"\"\n{review_excerpt}\n\"\"\"

Based on this, does the reviewer recommend the movie? 
Reply only with Yes or No and a one-line explanation.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()
