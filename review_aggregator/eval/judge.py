"""Judge panel scoring for LLM outputs."""

import asyncio
import argparse
import json
import time
from pathlib import Path
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from review_aggregator.llm.client import process_with_llm
from review_aggregator.utils.logger import get_logger
from review_aggregator.eval.db import (
    get_latest_batch,
    get_batch,
    get_unscored_outputs,
    get_sample,
    save_judge_score,
)

logger = get_logger(__name__)


class FieldScore(BaseModel):
    """Score for a single field."""
    score: int = Field(
        description="Score: 1 for pass/correct, 0 for fail/incorrect"
    )
    reasoning: str = Field(
        description="Brief explanation for the score (1-2 sentences)"
    )


class JudgeOutput(BaseModel):
    """Judge's evaluation of an LLM output."""
    score_is_film_review: FieldScore = Field(
        description="Judgment on is_film_review classification correctness"
    )
    score_movie_names: FieldScore = Field(
        description="Judgment on movie_names extraction quality"
    )
    score_sentiment: FieldScore = Field(
        description="Judgment on sentiment classification correctness"
    )
    score_cleaned_title: FieldScore = Field(
        description="Judgment on cleaned_title quality and accuracy"
    )
    score_cleaned_short_review: FieldScore = Field(
        description="Judgment on cleaned_short_review quality and accuracy"
    )


def get_judge_prompt(judge_model: str) -> tuple[str, str]:
    """Get system and user prompt templates for judge."""
    system_prompt = """You are an expert evaluator of movie review analysis systems.

Your task: Evaluate the quality of extracted fields from a movie review.

## Scoring Guidelines

Score 1 if: The extracted field is accurate, complete, and of high quality.
Score 0 if: The extracted field is inaccurate, incomplete, or of poor quality.

### is_film_review
- Score 1: Correctly identifies whether content is a film review (true/false)
- Score 0: Misclassifies the review type

### movie_names
- Score 1: Correctly extracts all relevant film titles mentioned
- Score 0: Missing important films or includes irrelevant titles

### sentiment
- Score 1: Sentiment (Positive/Negative/Neutral) accurately reflects reviewer's opinion
- Score 0: Sentiment misrepresents the review's tone

### cleaned_title
- Score 1: Title is clean, readable, and accurately represents the review topic
- Score 0: Title is unclear, contains artifacts, or misrepresents content

### cleaned_short_review
- Score 1: Summary captures key points, is well-written, and under 280 characters
- Score 0: Summary is unclear, incomplete, or poorly written

Provide brief reasoning for each score."""

    user_prompt_template = """Evaluate this LLM output:

**Input Title:** {input_title}

**Input Summary:** {input_summary}

**Input Full Review (first 500 chars):** {input_full_review_preview}

**LLM Output:**
- is_film_review: {output_is_film_review}
- movie_names: {output_movie_names}
- sentiment: {output_sentiment}
- cleaned_title: {output_cleaned_title}
- cleaned_short_review: {output_cleaned_short_review}

Score each field as 1 (pass) or 0 (fail) with brief reasoning."""

    return system_prompt, user_prompt_template


async def score_output_with_judge(
    llm_output: dict,
    sample: dict,
    judge_model: str,
) -> dict:
    """
    Score a single LLM output using a judge model.

    Returns dict with scores or error.
    """
    output_id = llm_output["id"]
    start_time = time.time()

    try:
        system_prompt, user_prompt_template = get_judge_prompt(judge_model)

        # Preview of full review (first 500 chars)
        full_review_preview = (sample.get("input_full_review") or "")[:500]

        user_prompt = user_prompt_template.format(
            input_title=sample.get("input_title", ""),
            input_summary=sample.get("input_summary", ""),
            input_full_review_preview=full_review_preview,
            output_is_film_review=llm_output.get("output_is_film_review"),
            output_movie_names=llm_output.get("output_movie_names", "[]"),
            output_sentiment=llm_output.get("output_sentiment"),
            output_cleaned_title=llm_output.get("output_cleaned_title", ""),
            output_cleaned_short_review=llm_output.get("output_cleaned_short_review", ""),
        )

        judge_output = await process_with_llm(
            model=judge_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=JudgeOutput,
        )

        latency_ms = (time.time() - start_time) * 1000

        return {
            "llm_output_id": output_id,
            "judge_model": judge_model,
            "error": None,
            "latency_ms": latency_ms,
            "scores": judge_output,
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Error scoring output {output_id} with {judge_model}: {e}")

        return {
            "llm_output_id": output_id,
            "judge_model": judge_model,
            "error": str(e),
            "latency_ms": latency_ms,
            "scores": None,
        }


async def score_outputs(
    batch_id: str = "latest",
    judges: list[str] = None,
    concurrency: int = 2,
) -> dict:
    """
    Score unscored LLM outputs with judge panel.

    Args:
        batch_id: Batch ID or 'latest'
        judges: List of judge models (e.g., ["anthropic/claude-sonnet-4-20250514"])
        concurrency: Max concurrent judge requests

    Returns:
        Statistics dict
    """
    if judges is None:
        judges = ["anthropic/claude-sonnet-4-20250514"]

    # Get batch
    if batch_id == "latest":
        batch = get_latest_batch()
        if not batch:
            raise ValueError("No batches found")
        batch_id = batch["id"]
    else:
        batch = get_batch(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

    logger.info(f"Scoring outputs for batch {batch_id}")

    # Get unscored outputs
    outputs = get_unscored_outputs(batch_id=batch_id)
    logger.info(f"Found {len(outputs)} unscored outputs")

    if not outputs:
        logger.info("No unscored outputs found")
        return {
            "batch_id": batch_id,
            "judges": judges,
            "output_count": 0,
            "score_count": 0,
            "success_count": 0,
            "error_count": 0,
        }

    # Run judges with concurrency control
    semaphore = asyncio.Semaphore(concurrency)

    async def run_with_semaphore(output, judge):
        async with semaphore:
            sample = get_sample(output["sample_id"])
            return await score_output_with_judge(output, sample, judge)

    # Collect all tasks
    tasks = []
    for output in outputs:
        for judge in judges:
            tasks.append(run_with_semaphore(output, judge))

    results = await asyncio.gather(*tasks)

    # Save scores to eval.db
    success_count = 0
    error_count = 0

    for result in results:
        if result["error"]:
            error_count += 1
            logger.error(f"Output {result['llm_output_id']} scored by {result['judge_model']}: {result['error']}")
        else:
            success_count += 1
            scores = result["scores"]

            # Extract scores
            save_judge_score(
                llm_output_id=result["llm_output_id"],
                judge_model=result["judge_model"],
                score_is_film_review=scores.score_is_film_review.score,
                score_movie_names=scores.score_movie_names.score,
                score_sentiment=scores.score_sentiment.score,
                score_cleaned_title=scores.score_cleaned_title.score,
                score_cleaned_short_review=scores.score_cleaned_short_review.score,
                reasoning=json.dumps({
                    "is_film_review": scores.score_is_film_review.reasoning,
                    "movie_names": scores.score_movie_names.reasoning,
                    "sentiment": scores.score_sentiment.reasoning,
                    "cleaned_title": scores.score_cleaned_title.reasoning,
                    "cleaned_short_review": scores.score_cleaned_short_review.reasoning,
                }),
            )

    logger.info(f"Scoring complete: {success_count} successes, {error_count} errors")

    return {
        "batch_id": batch_id,
        "judges": judges,
        "output_count": len(outputs),
        "score_count": len(results),
        "success_count": success_count,
        "error_count": error_count,
        "mean_latency_ms": sum(r["latency_ms"] for r in results) / len(results) if results else 0,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Score LLM outputs with judge panel")
    parser.add_argument("--batch", type=str, default="latest", help="Batch ID or 'latest'")
    parser.add_argument("--judges", nargs="+", default=["anthropic/claude-sonnet-4-20250514"],
                       help="Judge models (e.g., anthropic/claude-sonnet-4-20250514)")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent judges")
    args = parser.parse_args()

    stats = asyncio.run(score_outputs(
        batch_id=args.batch,
        judges=args.judges,
        concurrency=args.concurrency,
    ))

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
