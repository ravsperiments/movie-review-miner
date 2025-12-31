"""Evaluation framework - run model+prompt against golden set."""
import asyncio
import json
import importlib
import logging
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

from review_aggregator.llm.client import process_with_llm
from review_aggregator.llm.schemas import ProcessedReview

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def fuzzy_match(actual: str, expected: str, threshold: float = 0.8) -> tuple[bool, float]:
    """Check if strings match above similarity threshold."""
    if not actual or not expected:
        return actual == expected, 1.0 if actual == expected else 0.0
    similarity = SequenceMatcher(None, actual.lower(), expected.lower()).ratio()
    return similarity >= threshold, round(similarity, 3)


def compare_outputs(actual: ProcessedReview, expected: dict) -> dict:
    """Compare actual LLM output against expected values."""
    results = {}

    # Exact match for boolean
    results["is_film_review"] = {
        "pass": actual.is_film_review == expected["is_film_review"],
        "actual": actual.is_film_review,
        "expected": expected["is_film_review"],
    }

    # Exact match for sentiment
    results["sentiment"] = {
        "pass": actual.sentiment == expected["sentiment"],
        "actual": actual.sentiment,
        "expected": expected["sentiment"],
    }

    # Set comparison for movie names (case-insensitive, order doesn't matter)
    actual_movies = set(m.lower() for m in actual.movie_names)
    expected_movies = set(m.lower() for m in expected.get("movie_names", []))
    results["movie_names"] = {
        "pass": actual_movies == expected_movies,
        "actual": actual.movie_names,
        "expected": expected.get("movie_names", []),
    }

    # Fuzzy match for text fields
    title_pass, title_sim = fuzzy_match(
        actual.cleaned_title,
        expected["cleaned_title"],
        threshold=0.85
    )
    results["cleaned_title"] = {
        "pass": title_pass,
        "similarity": title_sim,
        "actual": actual.cleaned_title,
        "expected": expected["cleaned_title"],
    }

    summary_pass, summary_sim = fuzzy_match(
        actual.cleaned_short_review,
        expected["cleaned_short_review"],
        threshold=0.7  # More lenient for summaries
    )
    results["cleaned_short_review"] = {
        "pass": summary_pass,
        "similarity": summary_sim,
        "actual": actual.cleaned_short_review,
        "expected": expected["cleaned_short_review"],
    }

    # Overall pass requires all fields to pass
    results["all_passed"] = all(
        r["pass"] for r in results.values() if isinstance(r, dict) and "pass" in r
    )

    return results


async def run_single_test(
    test_case: dict,
    model: str,
    prompt_module,
) -> dict:
    """Run a single test case."""
    test_id = test_case["id"]
    input_data = test_case["input"]
    expected = test_case["expected"]

    start_time = datetime.now()

    try:
        user_prompt = prompt_module.USER_PROMPT_TEMPLATE.format(
            title=input_data.get("title", ""),
            summary=input_data.get("summary", ""),
            full_review=input_data.get("full_review", ""),
        )

        actual = await process_with_llm(
            model=model,
            system_prompt=prompt_module.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=ProcessedReview,
        )

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        comparison = compare_outputs(actual, expected)

        return {
            "test_id": test_id,
            "passed": comparison["all_passed"],
            "latency_ms": round(latency_ms, 2),
            "actual": actual.model_dump(),
            "expected": expected,
            "field_results": comparison,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Test {test_id} failed with error: {e}")
        return {
            "test_id": test_id,
            "passed": False,
            "latency_ms": None,
            "actual": None,
            "expected": expected,
            "field_results": None,
            "error": str(e),
        }


async def run_evaluation(
    model: str,
    prompt_version: str,
    golden_set_path: str = None,
    concurrency: int = 3,
) -> dict:
    """
    Run model+prompt combination against golden set.

    Args:
        model: LLM to evaluate (e.g., "anthropic/claude-3-5-sonnet-latest")
        prompt_version: Prompt version to test
        golden_set_path: Path to golden set JSON
        concurrency: Max concurrent test runs

    Returns:
        Evaluation report dict
    """
    # Load golden set
    if golden_set_path is None:
        golden_set_path = Path(__file__).parent / "golden_set.json"
    else:
        golden_set_path = Path(golden_set_path)

    with open(golden_set_path) as f:
        golden_data = json.load(f)

    test_cases = golden_data.get("test_cases", golden_data)
    if isinstance(test_cases, dict):
        test_cases = [test_cases]

    # Load prompt
    prompt_module = importlib.import_module(
        f"crawler.llm.prompts.process_review_{prompt_version}"
    )

    logger.info(f"Running evaluation: model={model}, prompt={prompt_version}, tests={len(test_cases)}")

    # Run tests with concurrency control
    semaphore = asyncio.Semaphore(concurrency)

    async def run_with_semaphore(tc):
        async with semaphore:
            return await run_single_test(tc, model, prompt_module)

    results = await asyncio.gather(*[
        run_with_semaphore(tc) for tc in test_cases
    ])

    # Calculate metrics
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    # Field-level accuracy
    field_stats = {}
    for field in ["is_film_review", "sentiment", "movie_names", "cleaned_title", "cleaned_short_review"]:
        field_passes = sum(
            1 for r in results
            if r["field_results"] and r["field_results"].get(field, {}).get("pass", False)
        )
        field_stats[field] = round(field_passes / len(results), 3) if results else 0

    # Build report
    report = {
        "meta": {
            "model": model,
            "prompt_version": prompt_version,
            "prompt_description": prompt_module.DESCRIPTION,
            "timestamp": datetime.now().isoformat(),
            "golden_set_version": golden_data.get("version", "unknown"),
            "total_cases": len(results),
        },
        "summary": {
            "passed": passed,
            "failed": failed,
            "accuracy": round(passed / len(results), 3) if results else 0,
            "field_accuracy": field_stats,
        },
        "failures": [
            {
                "test_id": r["test_id"],
                "error": r["error"],
                "field_results": {
                    k: v for k, v in (r["field_results"] or {}).items()
                    if isinstance(v, dict) and not v.get("pass", True)
                } if r["field_results"] else None
            }
            for r in results if not r["passed"]
        ],
        "details": results,
    }

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    safe_model = model.replace("/", "_")
    filename = f"eval_{safe_model}_{prompt_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = RESULTS_DIR / filename

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Evaluation complete: {passed}/{len(results)} passed ({report['summary']['accuracy']:.1%})")
    logger.info(f"Results saved to: {output_path}")

    return report
