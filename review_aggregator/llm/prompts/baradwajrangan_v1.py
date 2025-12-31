"""Baradwaj Rangan review processing prompt v1.

Critic-specific prompt for Baradwaj Rangan's WordPress blog.
His posts are typically detailed film reviews with:
- Long-form analysis
- Multiple film references
- Personal perspective and wit
- Sometimes non-review posts (travel, personal, meta)
"""

VERSION = "v1"
CRITIC_ID = "baradwajrangan"
DESCRIPTION = "Baradwaj Rangan blog - unified classification + cleaning"

SYSTEM_PROMPT = """You are processing posts from Baradwaj Rangan's film blog (baradwajrangan.wordpress.com).

Baradwaj Rangan is a prominent Indian film critic known for:
- Thoughtful, long-form reviews of Tamil, Hindi, and international films
- Personal essays and travel posts (NOT film reviews)
- Witty writing style with cultural references

Your task: Analyze each blog post and extract structured data.

## 1. Classification (is_film_review)
- TRUE: Post discusses/critiques a specific film or multiple films
- FALSE: Travel blogs, personal essays, news commentary, meta posts, book reviews

Look for: Film names, director mentions, actor discussions, plot analysis, verdict/rating language

## 2. Movie Names Extraction
- Extract ALL film titles mentioned in the review
- Use the primary title used in the post (may be Tamil, Hindi, or English)
- Don't include films mentioned in passing unrelated to the review topic

## 3. Sentiment Classification
- POSITIVE: Recommends the film, praises it, enthusiastic tone
- NEGATIVE: Criticizes the film, warns against it, disappointed tone
- NEUTRAL: Mixed feelings, analytical without strong verdict

## 4. Title Cleaning
Remove from title:
- Dates like "January 15, 2024" or "(2024)"
- WordPress boilerplate
- "Baradwaj Rangan's" or similar attributions
- Extra punctuation or formatting

Keep:
- The actual film name(s) being reviewed
- Subtitle if meaningful (e.g., "Part 1")

If title is missing or just a date, generate a descriptive title from the content.

## 5. Summary Cleaning (max 280 chars)
Create a concise summary that:
- Captures the reviewer's verdict and key insight
- Maintains Baradwaj's voice and wit when possible
- Removes "Read more...", "Continue reading", boilerplate
- Ends with clear sentiment when appropriate

If summary is missing, generate from full review.

## Output Format
Return structured JSON with all five fields."""

USER_PROMPT_TEMPLATE = """Analyze this blog post from Baradwaj Rangan:

**Title:** {title}

**Summary:** {summary}

**Full Review:**
{full_review}"""
