import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def is_film_review(title: str, short_review: str) -> str:
    """Return 'Yes' or 'No' along with a short explanation."""
    prompt = f"""
Given the following blog post metadata:

Title:
"""{title}"""

Short Review Snippet:
"""{short_review}"""

Does this appear to be a film review?
Reply with Yes or No, followed by a one-line reason.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()

def analyze_sentiment(title: str, subtext: str) -> str:
    """Return whether the reviewer recommends the movie as Yes, No or Maybe."""
    prompt = f"""
You are an expert assistant analysing film reviews from the blog
baradwajrangan.wordpress.com. Some posts on this site are not
actual movie reviews while others, like the one on "DNA" by Nelson,
are strongly negative. Keep these nuances in mind.

Below are the post title and a short blurb from the review:

Title:
"""{title}"""

Subtext:
"""{subtext}"""

Determine whether the author recommends watching the movie.
Look for sarcasm or negative phrasing.
If the snippet does not appear to actually contain a movie review,
reply with "No – not a review".
Otherwise answer "Yes", "No" or "Maybe" followed by a concise reason.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()

