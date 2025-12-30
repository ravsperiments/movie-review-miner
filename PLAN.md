# Pipeline Refactoring Plan

## Summary
Simplify the movie review mining pipeline by:
1. Replacing 8 LLM wrappers with **Instructor + native SDKs**
2. Consolidating 4 LLM calls per review into **1 unified call**
3. Adding structured **experimentation framework** with golden set evaluation
4. Organizing prompts into **versioned files** for A/B testing

---

## Pipeline Structure (3 Steps)

```
1. CRAWL        → Fetch links + Parse pages (no LLM)
2. EXTRACT      → Single LLM call: classify + clean + sentiment
3. ENRICH       → Add TMDB metadata (posters, year, cast)
```

---

## New Architecture

### Directory Structure
```
crawler/
├── llm/
│   ├── client.py                    # Instructor-based unified client
│   ├── schemas.py                   # Pydantic output models
│   └── prompts/
│       ├── process_review_v1.py     # Versioned prompts
│       └── process_review_v2.py
├── pipeline/
│   ├── fetch_and_parse.py           # Scraping (keep existing)
│   └── process_reviews.py           # Single LLM orchestrator (NEW)
├── eval/
│   ├── runner.py                    # Experiment runner
│   ├── golden_set.json              # Test inputs + expected outputs
│   └── results/                     # JSON result files per experiment
├── db/                              # (unchanged)
├── scraper/                         # (unchanged)
├── utils/                           # (unchanged)
└── run_pipeline.py                  # Simplified CLI entry point
```

---

## Files to Create

### 1. `crawler/llm/client.py` - Unified LLM Client
```python
import instructor
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel
import os

# Initialize clients for each provider
_clients = {}

def get_client(provider: str):
    """Get or create instructor-patched client for provider."""
    if provider not in _clients:
        if provider == "anthropic":
            _clients[provider] = instructor.from_anthropic(AsyncAnthropic())
        elif provider == "openai":
            _clients[provider] = instructor.from_openai(AsyncOpenAI())
        elif provider == "groq":
            _clients[provider] = instructor.from_openai(
                AsyncOpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=os.getenv("GROQ_API_KEY")
                )
            )
        elif provider == "ollama":
            _clients[provider] = instructor.from_openai(
                AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    return _clients[provider]

def parse_model_string(model: str) -> tuple[str, str]:
    """Parse 'provider/model' into (provider, model_name)."""
    if "/" in model:
        provider, model_name = model.split("/", 1)
    else:
        # Default to anthropic for unprefixed models
        provider, model_name = "anthropic", model
    return provider, model_name

async def process_with_llm(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    max_retries: int = 3,
) -> BaseModel:
    """
    Call any LLM with structured output.

    Args:
        model: Provider/model string (e.g., "anthropic/claude-3-5-sonnet-latest")
        system_prompt: System instructions
        user_prompt: User message with data
        response_model: Pydantic model for structured output
        max_retries: Retry attempts for validation errors

    Returns:
        Parsed Pydantic model instance
    """
    provider, model_name = parse_model_string(model)
    client = get_client(provider)

    if provider == "anthropic":
        return await client.messages.create(
            model=model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            response_model=response_model,
            max_retries=max_retries,
        )
    else:
        # OpenAI-compatible (OpenAI, Groq, Ollama)
        return await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=response_model,
            max_retries=max_retries,
        )
```

---

### 2. `crawler/llm/schemas.py` - Output Models
```python
from pydantic import BaseModel, Field

class ProcessedReview(BaseModel):
    """Unified output for review processing - combines classification + cleaning."""

    is_film_review: bool = Field(
        description="True if this content is a film/movie review"
    )
    movie_names: list[str] = Field(
        default_factory=list,
        description="List of film titles mentioned in the review"
    )
    sentiment: str = Field(
        description="Overall sentiment: Positive, Negative, or Neutral"
    )
    cleaned_title: str = Field(
        description="Clean title without dates, 'Review:' prefix, or site names"
    )
    cleaned_short_review: str = Field(
        description="Concise summary of the review, max 280 characters"
    )
```

---

### 3. `crawler/llm/prompts/process_review_v1.py` - Initial Prompt
```python
VERSION = "v1"
DESCRIPTION = "Initial unified prompt - classification + cleaning in one call"

SYSTEM_PROMPT = """You are a film review processor. Analyze the given blog post and:

1. **Classification**: Determine if this is a film/movie review
2. **Extraction**: List all film titles mentioned
3. **Sentiment**: Classify overall sentiment (Positive/Negative/Neutral)
4. **Clean Title**: Remove noise from the title
5. **Clean Summary**: Create a concise summary (max 280 chars)

## Title Cleaning Rules
- Remove dates (e.g., "January 2024", "(2024)")
- Remove prefixes like "Review:", "Film Review:", "Movie:"
- Remove site names and author attributions
- Keep the core film title and any meaningful descriptors
- If title is missing or just a date, generate from content

## Summary Rules
- Maximum 280 characters
- Capture the essence and verdict of the review
- If summary is missing, generate from the full review
- Use the reviewer's voice and style
- End with clear sentiment indicator

## Output Format
Return a JSON object with these exact fields:
- is_film_review: boolean
- movie_names: array of strings
- sentiment: "Positive" | "Negative" | "Neutral"
- cleaned_title: string
- cleaned_short_review: string (max 280 chars)
"""

USER_PROMPT_TEMPLATE = """Analyze this blog post:

**Title:** {title}

**Summary:** {summary}

**Full Review:**
{full_review}
"""
```

---

### 4. `crawler/pipeline/process_reviews.py` - Pipeline Orchestrator
```python
import asyncio
import importlib
import logging
from typing import Optional

from crawler.llm.client import process_with_llm
from crawler.llm.schemas import ProcessedReview
from crawler.db.scraper_queries import get_staged_reviews, update_page_status
from crawler.db.stg_clean_review_queries import upsert_clean_review

logger = logging.getLogger(__name__)

async def process_single_review(
    page: dict,
    model: str,
    prompt_module,
) -> tuple[str, Optional[ProcessedReview], Optional[str]]:
    """
    Process a single review through the LLM.

    Returns:
        Tuple of (page_id, result, error)
    """
    page_id = page["id"]

    try:
        user_prompt = prompt_module.USER_PROMPT_TEMPLATE.format(
            title=page.get("parsed_title", "") or "",
            summary=page.get("parsed_short_review", "") or "",
            full_review=page.get("parsed_full_review", "") or "",
        )

        result = await process_with_llm(
            model=model,
            system_prompt=prompt_module.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=ProcessedReview,
        )

        logger.info(f"Processed {page_id}: is_film_review={result.is_film_review}")
        return page_id, result, None

    except Exception as e:
        logger.error(f"Failed to process {page_id}: {e}")
        return page_id, None, str(e)


async def run_pipeline(
    model: str = "anthropic/claude-3-5-sonnet-latest",
    prompt_version: str = "v1",
    limit: int = 10,
    dry_run: bool = False,
    concurrency: int = 5,
) -> dict:
    """
    Run the review processing pipeline.

    Args:
        model: LLM to use (e.g., "anthropic/claude-3-5-sonnet-latest")
        prompt_version: Prompt version to use (e.g., "v1")
        limit: Maximum reviews to process
        dry_run: If True, don't write to database
        concurrency: Max concurrent LLM calls

    Returns:
        Summary dict with counts and errors
    """
    # Load prompt module
    prompt_module = importlib.import_module(
        f"crawler.llm.prompts.process_review_{prompt_version}"
    )
    logger.info(f"Using prompt {prompt_version}: {prompt_module.DESCRIPTION}")

    # Fetch unprocessed pages
    pages = get_staged_reviews(limit=limit)
    logger.info(f"Fetched {len(pages)} pages to process")

    if not pages:
        return {"processed": 0, "film_reviews": 0, "errors": 0}

    # Process with controlled concurrency
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_semaphore(page):
        async with semaphore:
            return await process_single_review(page, model, prompt_module)

    results = await asyncio.gather(*[
        process_with_semaphore(page) for page in pages
    ])

    # Aggregate results
    processed = 0
    film_reviews = 0
    errors = []

    for page_id, result, error in results:
        if error:
            errors.append({"page_id": page_id, "error": error})
            continue

        processed += 1

        if result.is_film_review:
            film_reviews += 1

            if not dry_run:
                # Store cleaned review
                upsert_clean_review(
                    source_id=page_id,
                    cleaned_title=result.cleaned_title,
                    cleaned_short_review=result.cleaned_short_review,
                    movie_names=result.movie_names,
                    sentiment=result.sentiment,
                )

        if not dry_run:
            update_page_status(page_id, "processed")

    summary = {
        "processed": processed,
        "film_reviews": film_reviews,
        "non_reviews": processed - film_reviews,
        "errors": len(errors),
        "error_details": errors if errors else None,
        "model": model,
        "prompt_version": prompt_version,
    }

    logger.info(f"Pipeline complete: {summary}")
    return summary
```

---

### 5. `crawler/eval/runner.py` - Evaluation Framework
```python
import asyncio
import json
import importlib
import logging
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

from crawler.llm.client import process_with_llm
from crawler.llm.schemas import ProcessedReview

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def fuzzy_match(actual: str, expected: str, threshold: float = 0.8) -> tuple[bool, float]:
    """Check if strings match above similarity threshold."""
    similarity = SequenceMatcher(None, actual.lower(), expected.lower()).ratio()
    return similarity >= threshold, similarity


def compare_outputs(actual: ProcessedReview, expected: dict) -> dict:
    """Compare actual LLM output against expected values."""
    results = {}

    # Exact matches
    results["is_film_review"] = {
        "pass": actual.is_film_review == expected["is_film_review"],
        "actual": actual.is_film_review,
        "expected": expected["is_film_review"],
    }

    results["sentiment"] = {
        "pass": actual.sentiment == expected["sentiment"],
        "actual": actual.sentiment,
        "expected": expected["sentiment"],
    }

    # Set comparison for movie names
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

    # Overall pass
    results["all_passed"] = all(r["pass"] for r in results.values() if isinstance(r, dict))

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
                }
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
```

---

### 6. `crawler/eval/golden_set.json` - Test Data
```json
{
  "version": "1.0",
  "description": "Golden set for review processing evaluation",
  "test_cases": [
    {
      "id": "tc_001",
      "input": {
        "title": "Review: Inception (2010) - A Mind-Bending Masterpiece | FilmBlog",
        "summary": "",
        "full_review": "Christopher Nolan delivers another cerebral thriller that challenges viewers to question the nature of reality. The film follows Dom Cobb, a skilled thief who extracts secrets from people's dreams. With stunning visuals and a complex narrative, Inception is a must-watch for any cinema enthusiast."
      },
      "expected": {
        "is_film_review": true,
        "movie_names": ["Inception"],
        "sentiment": "Positive",
        "cleaned_title": "Inception",
        "cleaned_short_review": "Christopher Nolan delivers a cerebral thriller that challenges viewers to question reality. With stunning visuals and complex narrative, this dream-heist film is a must-watch."
      },
      "tags": ["positive", "missing_summary", "nolan"]
    },
    {
      "id": "tc_002",
      "input": {
        "title": "My Trip to Goa - Travel Diary",
        "summary": "Beautiful beaches and great food",
        "full_review": "Last week I visited Goa with my family. The beaches were pristine and the seafood was amazing. We stayed at a lovely resort near Baga beach. Highly recommend visiting during off-season for fewer crowds."
      },
      "expected": {
        "is_film_review": false,
        "movie_names": [],
        "sentiment": "Neutral",
        "cleaned_title": "My Trip to Goa - Travel Diary",
        "cleaned_short_review": "Beautiful beaches and great food"
      },
      "tags": ["non_review", "travel"]
    }
  ]
}
```

---

### 7. `crawler/run_pipeline.py` - CLI Entry Point
```python
#!/usr/bin/env python3
"""
Movie Review Miner - Pipeline CLI

Usage:
    # Run production pipeline
    python run_pipeline.py --mode pipeline --model anthropic/claude-3-5-sonnet-latest --prompt v1 --limit 10

    # Run evaluation
    python run_pipeline.py --mode eval --model anthropic/claude-3-5-sonnet-latest --prompt v1

    # Dry run (no DB writes)
    python run_pipeline.py --mode pipeline --dry-run
"""
import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Movie Review Miner Pipeline")

    parser.add_argument(
        "--mode",
        choices=["pipeline", "eval"],
        default="pipeline",
        help="Run mode: 'pipeline' for production, 'eval' for experimentation"
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-3-5-sonnet-latest",
        help="LLM to use (e.g., anthropic/claude-3-5-sonnet-latest, groq/llama-3.1-70b-versatile)"
    )
    parser.add_argument(
        "--prompt",
        default="v1",
        help="Prompt version (e.g., v1, v2)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max reviews to process (pipeline mode)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write to database"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent LLM calls"
    )

    args = parser.parse_args()

    if args.mode == "pipeline":
        from crawler.pipeline.process_reviews import run_pipeline

        logger.info(f"Starting pipeline: model={args.model}, prompt={args.prompt}, limit={args.limit}")
        result = asyncio.run(run_pipeline(
            model=args.model,
            prompt_version=args.prompt,
            limit=args.limit,
            dry_run=args.dry_run,
            concurrency=args.concurrency,
        ))

        print(f"\n{'='*50}")
        print("PIPELINE SUMMARY")
        print(f"{'='*50}")
        print(f"Processed:    {result['processed']}")
        print(f"Film Reviews: {result['film_reviews']}")
        print(f"Non-Reviews:  {result['non_reviews']}")
        print(f"Errors:       {result['errors']}")

    else:  # eval mode
        from crawler.eval.runner import run_evaluation

        logger.info(f"Starting evaluation: model={args.model}, prompt={args.prompt}")
        result = asyncio.run(run_evaluation(
            model=args.model,
            prompt_version=args.prompt,
            concurrency=args.concurrency,
        ))

        print(f"\n{'='*50}")
        print("EVALUATION SUMMARY")
        print(f"{'='*50}")
        print(f"Model:    {result['meta']['model']}")
        print(f"Prompt:   {result['meta']['prompt_version']}")
        print(f"Accuracy: {result['summary']['accuracy']:.1%}")
        print(f"Passed:   {result['summary']['passed']}/{result['meta']['total_cases']}")
        print(f"\nField Accuracy:")
        for field, acc in result['summary']['field_accuracy'].items():
            print(f"  {field}: {acc:.1%}")

        if result['failures']:
            print(f"\nFailures:")
            for f in result['failures'][:5]:  # Show first 5
                print(f"  - {f['test_id']}: {f.get('error') or list(f['field_results'].keys())}")


if __name__ == "__main__":
    main()
```

---

## Files to DELETE

After new implementation is working:

```
crawler/llm/
├── anthropic_wrapper.py      # DELETE
├── openai_wrapper.py         # DELETE
├── groq_wrapper.py           # DELETE
├── gemini_wrapper.py         # DELETE
├── mistral_wrapper.py        # DELETE
├── xai_wrapper.py            # DELETE
├── huggingface_wrapper.py    # DELETE
├── ollama_wrapper.py         # DELETE
├── llm_controller.py         # DELETE
└── reconcile_llm_output/     # DELETE (entire folder)

crawler/pipeline/
├── classify_review_orchestrator.py  # DELETE
└── clean_review_orchestrator.py     # DELETE

crawler/llm/prompts/
├── clean_review_system_prompt.py           # DELETE
├── judge_clean_review_system_prompt.py     # DELETE
└── page_classification_system_prompt.py    # DELETE
```

---

## Dependencies

Add to `requirements.txt`:
```
instructor>=1.0.0
anthropic>=0.39.0
openai>=1.0.0
```

Remove (no longer needed):
```
# Individual provider SDKs that were only used by deleted wrappers
```

---

## Migration Steps

1. **Add dependencies**: `pip install instructor`
2. **Create new files**: client.py, schemas.py, process_review_v1.py, runner.py, process_reviews.py
3. **Update run_pipeline.py** with new CLI
4. **Create golden_set.json** with test cases (can migrate from existing eval_data.json)
5. **Test new pipeline** on a few records with `--dry-run`
6. **Run evaluation** to validate quality
7. **Delete old files** once satisfied
8. **Update any imports** in remaining code

---

## Usage Examples

```bash
# Production: Process 10 reviews
python crawler/run_pipeline.py --mode pipeline --limit 10

# Production: Use Groq for faster/cheaper processing
python crawler/run_pipeline.py --mode pipeline --model groq/llama-3.1-70b-versatile

# Evaluation: Test Claude with v1 prompt
python crawler/run_pipeline.py --mode eval --model anthropic/claude-3-5-sonnet-latest --prompt v1

# Evaluation: Compare Groq performance
python crawler/run_pipeline.py --mode eval --model groq/llama-3.1-70b-versatile --prompt v1

# Evaluation: Test new prompt version
python crawler/run_pipeline.py --mode eval --prompt v2

# Dry run to see what would happen
python crawler/run_pipeline.py --mode pipeline --dry-run --limit 5
```
