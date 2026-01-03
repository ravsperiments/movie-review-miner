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
    get_eval_db,
)

logger = get_logger(__name__)


class JudgeOutput(BaseModel):
    """Judge's evaluation of an LLM output.

    All scores are 0 or 1. When is_film_review output is false,
    other scores should be null (not evaluated).
    """
    score_is_film_review: int = Field(
        description="1 if is_film_review classification is correct, 0 if incorrect. Always scored."
    )
    score_movie_names: int | None = Field(
        default=None,
        description="1 if movie_names extraction is correct, 0 if incorrect. Null if is_film_review=false."
    )
    score_sentiment: int | None = Field(
        default=None,
        description="1 if sentiment classification is correct, 0 if incorrect. Null if is_film_review=false."
    )
    score_cleaned_title: int | None = Field(
        default=None,
        description="1 if cleaned_title is good quality, 0 if poor quality. Null if is_film_review=false."
    )
    score_cleaned_short_review: int | None = Field(
        default=None,
        description="1 if cleaned_short_review is good quality, 0 if poor quality. Null if is_film_review=false."
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation for the scores"
    )


def get_judge_prompt(judge_model: str) -> tuple[str, str]:
    """Get system and user prompt templates for judge."""
    system_prompt = """You are an expert evaluator of movie review analysis systems.

Your task: Evaluate how well a model followed its task instructions and produced quality output.

## Conditional Scoring Rules

**IMPORTANT: If is_film_review output is FALSE:**
- Score is_film_review based on whether the classification is CORRECT (did model correctly identify non-review?)
- Set ALL other scores to null (do not evaluate movie_names, sentiment, title, summary)

**If is_film_review output is TRUE:**
- Score all fields normally

## Scoring Guidelines (when applicable)

### is_film_review (ALWAYS score this)
- Score 1: Correctly identifies whether content is a film review (true/false)
- Score 0: Misclassifies the review type

### movie_names (skip if is_film_review=false)
- Score 1: Correctly extracts all relevant film titles mentioned
- Score 0: Missing important films or includes irrelevant titles

### sentiment (skip if is_film_review=false)
- Score 1: Sentiment (Positive/Negative/Neutral) accurately reflects reviewer's opinion
- Score 0: Sentiment misrepresents the review's tone

### cleaned_title (skip if is_film_review=false)
- Score 1 if: Output matches original AND original was already good, OR output improved a problematic original
- Score 0 if: Output unnecessarily changed a good original, OR failed to fix a problematic original

### cleaned_short_review (skip if is_film_review=false)
- Score 1 if: Output matches original AND original was already good, OR output improved a problematic original
- Score 0 if: Output unnecessarily changed a good original, OR failed to fix a problematic original

Provide brief reasoning for your scores."""

    user_prompt_template = """Evaluate this LLM output against the task it was given.

## Original Task Given to Model

### System Prompt:
{system_prompt}

### User Prompt:
{user_prompt}

---

## Input Data (for reference)

**Input Title:** {input_title}

**Input Summary:** {input_summary}

**Input Full Review (first 500 chars):** {input_full_review_preview}

---

## Model Output to Evaluate

- is_film_review: {output_is_film_review}
- movie_names: {output_movie_names}
- sentiment: {output_sentiment}
- cleaned_title: {output_cleaned_title}
- cleaned_short_review: {output_cleaned_short_review}

---

Score each field based on whether the model correctly followed the task instructions.
Remember: If is_film_review is false, only score is_film_review and set other scores to null."""

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
        judge_system_prompt, user_prompt_template = get_judge_prompt(judge_model)

        # Preview of full review (first 500 chars)
        full_review_preview = (sample.get("input_full_review") or "")[:500]

        # Get original task prompts from llm_output (may be None for older outputs)
        original_system_prompt = llm_output.get("system_prompt") or "(Original system prompt not available)"
        original_user_prompt = llm_output.get("user_prompt") or "(Original user prompt not available)"

        user_prompt = user_prompt_template.format(
            system_prompt=original_system_prompt,
            user_prompt=original_user_prompt,
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
            system_prompt=judge_system_prompt,
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

            # Extract scores (now flat integers)
            save_judge_score(
                llm_output_id=result["llm_output_id"],
                judge_model=result["judge_model"],
                score_is_film_review=scores.score_is_film_review,
                score_movie_names=scores.score_movie_names,
                score_sentiment=scores.score_sentiment,
                score_cleaned_title=scores.score_cleaned_title,
                score_cleaned_short_review=scores.score_cleaned_short_review,
                reasoning=scores.reasoning,
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


SCORE_FIELDS = [
    "is_film_review",
    "movie_names",
    "sentiment",
    "cleaned_title",
    "cleaned_short_review",
]


def get_model_scores(batch_id: str = None) -> dict:
    """
    Aggregate judge scores by model.

    Returns:
        {
            "models": {
                "model_name": {
                    "field_scores": {"is_film_review": 0.85, ...},
                    "overall_score": 0.82,
                    "sample_count": 100,
                },
                ...
            },
            "field_averages": {"is_film_review": 0.80, ...},
        }
    """
    db = get_eval_db()

    # Query: join llm_outputs with judge_scores, grouped by model
    if batch_id:
        query = """
            SELECT
                lo.model,
                js.score_is_film_review,
                js.score_movie_names,
                js.score_sentiment,
                js.score_cleaned_title,
                js.score_cleaned_short_review
            FROM llm_outputs lo
            JOIN judge_scores js ON js.llm_output_id = lo.id
            JOIN samples s ON lo.sample_id = s.id
            WHERE s.batch_id = ?
        """
        rows = db.execute_query(query, (batch_id,), fetch=True)
    else:
        query = """
            SELECT
                lo.model,
                js.score_is_film_review,
                js.score_movie_names,
                js.score_sentiment,
                js.score_cleaned_title,
                js.score_cleaned_short_review
            FROM llm_outputs lo
            JOIN judge_scores js ON js.llm_output_id = lo.id
        """
        rows = db.execute_query(query, fetch=True)

    if not rows:
        return {"models": {}, "field_averages": {}}

    # Aggregate by model
    model_data = {}
    for row in rows:
        model = row["model"]
        if model not in model_data:
            model_data[model] = {field: [] for field in SCORE_FIELDS}

        for field in SCORE_FIELDS:
            score = row[f"score_{field}"]
            if score is not None:
                model_data[model][field].append(score)

    # Calculate averages per model
    models = {}
    for model, field_scores in model_data.items():
        field_avgs = {}
        all_scores = []
        for field in SCORE_FIELDS:
            scores = field_scores[field]
            if scores:
                avg = sum(scores) / len(scores)
                field_avgs[field] = avg
                all_scores.extend(scores)
            else:
                field_avgs[field] = None

        models[model] = {
            "field_scores": field_avgs,
            "overall_score": sum(all_scores) / len(all_scores) if all_scores else None,
            "sample_count": len(field_scores[SCORE_FIELDS[0]]),
        }

    # Calculate field averages across all models
    field_averages = {}
    for field in SCORE_FIELDS:
        all_field_scores = []
        for row in rows:
            score = row[f"score_{field}"]
            if score is not None:
                all_field_scores.append(score)
        field_averages[field] = sum(all_field_scores) / len(all_field_scores) if all_field_scores else None

    return {
        "models": models,
        "field_averages": field_averages,
    }


def print_model_comparison(batch_id: str = None) -> None:
    """Print a comparison table of model scores."""
    scores = get_model_scores(batch_id)

    if not scores["models"]:
        print("No scores found.")
        return

    # Header
    print("\n" + "=" * 100)
    print("MODEL COMPARISON")
    print("=" * 100)

    # Field headers (shortened)
    field_labels = {
        "is_film_review": "is_review",
        "movie_names": "movies",
        "sentiment": "sentiment",
        "cleaned_title": "title",
        "cleaned_short_review": "summary",
    }

    # Print header row
    header = f"{'Model':<45} | "
    header += " | ".join(f"{field_labels[f]:>8}" for f in SCORE_FIELDS)
    header += f" | {'Overall':>8} | {'N':>4}"
    print(header)
    print("-" * 100)

    # Sort by overall score descending
    sorted_models = sorted(
        scores["models"].items(),
        key=lambda x: x[1]["overall_score"] or 0,
        reverse=True,
    )

    # Print each model row
    for model, data in sorted_models:
        # Truncate model name if too long
        model_display = model[:43] + ".." if len(model) > 45 else model
        row = f"{model_display:<45} | "

        for field in SCORE_FIELDS:
            val = data["field_scores"].get(field)
            if val is not None:
                row += f"{val * 100:>7.1f}% | "
            else:
                row += f"{'N/A':>8} | "

        overall = data["overall_score"]
        if overall is not None:
            row += f"{overall * 100:>7.1f}% | "
        else:
            row += f"{'N/A':>8} | "

        row += f"{data['sample_count']:>4}"
        print(row)

    # Print field averages
    print("-" * 100)
    avg_row = f"{'AVERAGE':<45} | "
    overall_scores = []
    for field in SCORE_FIELDS:
        val = scores["field_averages"].get(field)
        if val is not None:
            avg_row += f"{val * 100:>7.1f}% | "
            overall_scores.append(val)
        else:
            avg_row += f"{'N/A':>8} | "

    if overall_scores:
        avg_row += f"{sum(overall_scores) / len(overall_scores) * 100:>7.1f}% |"
    else:
        avg_row += f"{'N/A':>8} |"
    print(avg_row)
    print("=" * 100 + "\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Score LLM outputs with judge panel")
    parser.add_argument("--batch", type=str, default="latest", help="Batch ID or 'latest'")
    parser.add_argument("--judges", nargs="+", default=["anthropic/claude-sonnet-4-20250514"],
                       help="Judge models (e.g., anthropic/claude-sonnet-4-20250514)")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent judges")
    parser.add_argument("--scores-only", action="store_true",
                       help="Only print model comparison (skip judging)")
    args = parser.parse_args()

    # Resolve batch ID
    if args.batch == "latest":
        batch = get_latest_batch()
        if not batch:
            print("No batches found")
            return
        batch_id = batch["id"]
    else:
        batch_id = args.batch

    if args.scores_only:
        # Just print scores without running judge
        print_model_comparison(batch_id)
        return

    stats = asyncio.run(score_outputs(
        batch_id=args.batch,
        judges=args.judges,
        concurrency=args.concurrency,
    ))

    print(json.dumps(stats, indent=2))

    # Print model comparison after judging
    print_model_comparison(batch_id)


if __name__ == "__main__":
    main()
