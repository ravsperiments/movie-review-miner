IS_FILM_REVIEW_PROMPT_TEMPLATE = """You are an expert critic assistant. Given the following blog post title and content, determine:

1. Is this a **film review**? (Yes/No/Maybe)
2. If yes, how many distinct **films** are being reviewed or discussed? If more than one, it is not a movie review, so say No
3. What are the **names of the films**, if mentioned?
4. Justify your answer briefly based on clues in the content.

Output your answer in the following JSON format:

{{
  "is_film_review": true | false | Maybe,
  "num_films": integer,
  "film_names": [list of strings],
  "justification": "short explanation"
}}

Here is the input:

---
Title: {blog_title}

Short Review: {short_review}

Full Review: {full_review}
---"""