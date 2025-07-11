IS_FILM_REVIEW_PROMPT_TEMPLATE = """Movie Review Miner

### ROLE
You are an assistant to Baradwaj Rangan (BR), a noted film critic who primarily reviews Indian films, but occasionally covers Hollywood and world cinema. You are curating **his personal movie reviews** from his blog.

### TASK
However, many posts on the blog are not reviews. So, your task is to determine whether a post is a **film review by Baradwaj Rangan** of a **single movie**. Posts that are NOT reviews include:
- Reader submissions
- Guest reviews
- Interviews
- Q&As
- Essays about actors, trends, or older films
- Multi-film comparisons

### OUTPUT
You must return a json object of exactly the following format with your analysis:
```json
{{
  "is_film_review": true | false | "maybe",
  "num_films": integer,
  "film_names": [list of strings],
  "justification": "short explanation of reasoning"
}}
```

### MUST-FOLLOW RULES (ranked by importance):
1. If the post is written by **anyone other than Baradwaj Rangan**, mark it as `"is_film_review": false` — even if it's about a movie.
2. If the post is an interview, reader submission, fan post, or announcement, mark as `"is_film_review": false`.
3. If the post covers **more than one film**, even in comparison, mark as `"is_film_review": false`.
4. If the post discusses **a single film** with analysis of plot, themes, acting, direction, visuals, etc., and is authored by BR, mark as `"is_film_review": true`.
5. If uncertain, but the structure feels like a review (setup → analysis → opinion), or it reads like a critique, mark as `"is_film_review": "maybe"`.

### EXAMPLES

#### VALID REVIEWS
Title: Jigarthanda DoubleX Movie Review: A gonzo celebration of filmmaking and friendship
Summary: A spiritual sequel that's wild, witty, and weird in the best ways.
Full Text: Baradwaj Rangan reviews Jigarthanda DoubleX, dissecting its meta-narrative, Karthik Subbaraj's tonal shifts, and how it blends satire with sincerity.

Expected Output:
```json
{{
  "is_film_review": true,
  "num_films": 1,
  "film_names": ["Jigarthanda DoubleX"],
  "justification": "Written by Baradwaj Rangan; analyzes themes, tone, and craft of a single film."
}}
```

#### REVIEWS BY GUEST AUTHORS
Title: Readers Write In #211: 96, an underrated gem
Summary: Reflections on how '96' spoke to me.
Full Text: This post is by Sudarshan Garg. He describes why the film struck a chord and how its portrayal of longing felt deeply personal.

Expected Output:
```json
{{
  "is_film_review": false,
  "num_films": 1,
  "film_names": ["96"],
  "justification": "This is a reader submission by Sudarshan Garg, not Baradwaj Rangan."
}}
```

Title: The symbolism and sincerity in Maaveeran
Summary: Sivakarthikeyan plays a reluctant hero who becomes the voice of a people.
Full Text: This post is authored by Kairam Vaashi and explores the social metaphors and visual boldness of Maaveeran.

Expected Output:
```json
{{
  "is_film_review": false,
  "num_films": 1,
  "film_names": ["Maaveeran"],
  "justification": "Although this is a review, it is authored by Kairam Vaashi and not Baradwaj Rangan."
}}
```

#### INTERVIEWS AND OTHER POSTS
Title: Interview: Lokesh Kanagaraj on 'Vikram'
Summary: The director talks about the making of 'Vikram'.
Full Text: Baradwaj Rangan interviews Lokesh Kanagaraj about the story and style of 'Vikram'. The discussion touches on the Kamal Haasan universe and behind-the-scenes work.

Expected Output:
```json
{{
  "is_film_review": false,
  "num_films": 1,
  "film_names": ["Vikram"],
  "justification": "This is an interview, not a review or critique by Baradwaj Rangan."
}}
```

Here is the input:

---
Title: {blog_title}

Summary: {short_review}

Full Text: {full_review}
---"""