"""Model evaluation runner - run models on sample batches."""

import asyncio
import argparse
import importlib
import json
import logging
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


def load_config() -> dict:
    """Load eval config from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def setup_eval_logging() -> logging.Logger:
    """Set up logging for eval: INFO to console, errors to file only."""
    logger = logging.getLogger("review_aggregator.eval.model_runner")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers.clear()
    logger.propagate = False

    # Console: INFO only (progress messages)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(console)

    # File: DEBUG and above (includes errors)
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "model_runner.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)

    return logger


from review_aggregator.llm.client import process_with_llm, parse_model_string
from review_aggregator.llm.schemas import ProcessedReview
from review_aggregator.eval.db import (
    get_latest_batch,
    get_batch,
    get_samples,
    save_llm_output,
)

logger = setup_eval_logging()

# Cache for imported prompt modules
_prompt_modules = {}


def get_critic_prompt(critic_id: str):
    """
    Auto-detect latest prompt version for a critic.

    Looks for pattern: review_aggregator/llm/prompts/{critic_id}_v{N}.py
    Returns the module with the highest version number.
    """
    cache_key = f"prompt_{critic_id}"
    if cache_key in _prompt_modules:
        return _prompt_modules[cache_key]

    # Normalize critic_id to valid Python module name (remove hyphens, lowercase)
    module_critic_id = critic_id.replace("-", "").lower()

    # Try to import the prompt module
    # Assumes prompt naming: critic_id_v1, critic_id_v2, etc.
    prompt_module = None
    version = 1

    while True:
        try:
            module_name = f"review_aggregator.llm.prompts.{module_critic_id}_v{version}"
            mod = importlib.import_module(module_name)
            prompt_module = mod
            version += 1
        except ImportError:
            break

    if not prompt_module:
        raise ValueError(f"No prompt found for critic {critic_id} (tried {module_critic_id}_v*)")

    _prompt_modules[cache_key] = prompt_module
    logger.info(f"Loaded prompt for {critic_id} (v{version - 1})")
    return prompt_module


async def run_sample_with_model(sample: dict, model: str, prompt_module) -> dict:
    """
    Run a single sample through a model.

    Returns dict with output or error.
    """
    sample_id = sample["id"]
    start_time = time.time()

    try:
        user_prompt = prompt_module.USER_PROMPT_TEMPLATE.format(
            title=sample.get("input_title", ""),
            summary=sample.get("input_summary", ""),
            full_review=sample.get("input_full_review", ""),
        )

        output = await process_with_llm(
            model=model,
            system_prompt=prompt_module.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=ProcessedReview,
        )

        latency_ms = (time.time() - start_time) * 1000

        return {
            "sample_id": sample_id,
            "model": model,
            "error": None,
            "latency_ms": latency_ms,
            "output": output,
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.debug(f"Error running sample {sample_id} on {model}: {e}")

        return {
            "sample_id": sample_id,
            "model": model,
            "error": str(e),
            "latency_ms": latency_ms,
            "output": None,
        }


async def run_eval(
    models: list[str],
    batch_id: str = "latest",
    limit: int = None,
    concurrency: int = 3,
) -> dict:
    """
    Run evaluation on a batch of samples.

    Args:
        models: List of model strings (e.g., ["anthropic/claude-sonnet-4-20250514"])
        batch_id: Batch ID or 'latest'
        limit: Max samples to process
        concurrency: Max concurrent requests

    Returns:
        Statistics dict
    """
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

    logger.info(f"Running eval on batch {batch_id}")

    # Get samples
    samples = get_samples(batch_id)
    if limit:
        samples = samples[:limit]

    logger.info(f"Processing {len(samples)} samples on {len(models)} models")

    # Load prompts for each critic
    critic_prompts = {}
    for sample in samples:
        critic = sample["critic_id"]
        if critic not in critic_prompts:
            try:
                critic_prompts[critic] = get_critic_prompt(critic)
            except Exception as e:
                logger.error(f"Failed to load prompt for critic {critic}: {e}")
                raise

    # Run models with concurrency control
    semaphore = asyncio.Semaphore(concurrency)

    async def run_with_semaphore(sample, model):
        async with semaphore:
            prompt = critic_prompts.get(sample["critic_id"])
            if not prompt:
                return {
                    "sample_id": sample["id"],
                    "model": model,
                    "error": f"No prompt for critic {sample['critic_id']}",
                    "latency_ms": 0,
                    "output": None,
                }
            return await run_sample_with_model(sample, model, prompt)

    # Collect all tasks
    tasks = []
    for sample in samples:
        for model in models:
            tasks.append(run_with_semaphore(sample, model))

    results = await asyncio.gather(*tasks)

    # Save results to eval.db
    success_count = 0
    error_count = 0

    for result in results:
        if result["error"]:
            error_count += 1
            logger.debug(f"Sample {result['sample_id']} on {result['model']}: {result['error']}")

            save_llm_output(
                sample_id=result["sample_id"],
                model=result["model"],
                prompt_version="unknown",
                error=result["error"],
                latency_ms=result["latency_ms"],
            )
        else:
            success_count += 1
            output = result["output"]

            # Get prompt version from critic
            sample = next(s for s in samples if s["id"] == result["sample_id"])
            critic = sample["critic_id"]
            prompt = critic_prompts[critic]
            prompt_version = getattr(prompt, "VERSION", "unknown")

            save_llm_output(
                sample_id=result["sample_id"],
                model=result["model"],
                prompt_version=prompt_version,
                output_is_film_review=output.is_film_review,
                output_movie_names=json.dumps(output.movie_names),
                output_sentiment=output.sentiment,
                output_cleaned_title=output.cleaned_title,
                output_cleaned_short_review=output.cleaned_short_review,
                latency_ms=result["latency_ms"],
            )

    logger.info(f"Eval complete: {success_count} successes, {error_count} errors")

    return {
        "batch_id": batch_id,
        "models": models,
        "sample_count": len(samples),
        "total_results": len(results),
        "success_count": success_count,
        "error_count": error_count,
        "mean_latency_ms": sum(r["latency_ms"] for r in results) / len(results) if results else 0,
    }


def main():
    """CLI entry point."""
    config = load_config()

    parser = argparse.ArgumentParser(description="Run model evaluation on sample batch")
    parser.add_argument("--models", nargs="+",
                       help="Models to evaluate (default: all from config.yaml)")
    parser.add_argument("--batch", type=str, default="latest", help="Batch ID or 'latest'")
    parser.add_argument("--limit", type=int, help="Max samples to process")
    parser.add_argument("--concurrency", type=int,
                       default=config.get("evaluation", {}).get("default_concurrency", 3),
                       help="Max concurrent requests")
    args = parser.parse_args()

    # Use models from config if not specified
    models = args.models or config.get("models", [])
    if not models:
        raise ValueError("No models specified. Add to config.yaml or use --models")

    print(f"Running eval with models: {models}")

    stats = asyncio.run(run_eval(
        models=models,
        batch_id=args.batch,
        limit=args.limit,
        concurrency=args.concurrency,
    ))

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
