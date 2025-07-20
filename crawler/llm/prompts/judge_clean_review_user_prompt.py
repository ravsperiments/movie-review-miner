# User prompt template for judge quality assessment
JUDGE_CLEAN_REVIEW_USER_PROMPT_TEMPLATE = """
Please assess the quality of this cleaned movie review content:

CLEANED TITLE: {title_to_judge}
CLEANED SHORT REVIEW: {short_review_to_judge}

ORIGINAL TITLE: {original_title}
ORIGINAL SHORT REVIEW: {original_short_review}
ORIGINAL FULL REVIEW: {original_full_review}

Evaluate if both the cleaned title and short review meet the professional standards expected for Baradwaj Rangan's film criticism.
"""