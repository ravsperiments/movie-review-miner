"""Sample batch creation from parsed pages."""

import argparse
import random
from pathlib import Path

from review_aggregator.db.sqlite_client import get_db
from review_aggregator.utils.logger import get_logger
from review_aggregator.eval.db import create_sample_batch, add_sample_to_batch

logger = get_logger(__name__)


def create_sample_batch_from_db(
    size: int,
    critic_id: str = None,
    mode: str = "per_critic",
    seed: int = 42,
) -> str:
    """
    Create a sample batch from parsed pages in local.db.

    Strategy:
    1. Query pages from local.db where status in ('parsed', 'extracted', 'enriched')
    2. Stratified random sampling by critic (if mode='per_critic')
    3. Store samples in eval.db with denormalized input data

    Args:
        size: Number of samples to collect
        critic_id: Optional critic ID to filter by (for per_critic mode)
        mode: 'per_critic' (proportional by critic) or 'across_all' (random all)
        seed: Random seed for reproducibility

    Returns:
        Batch ID
    """
    random.seed(seed)

    local_db = get_db()

    # Query candidates from local.db
    if critic_id:
        query = """
            SELECT id, critic_id,
                   parsed_title, parsed_short_review, parsed_full_review
            FROM pages
            WHERE status IN ('parsed', 'extracted', 'enriched')
              AND critic_id = ?
              AND LENGTH(COALESCE(parsed_title, '')) > 0
              AND LENGTH(COALESCE(parsed_full_review, '')) > 0
        """
        candidates = local_db.execute_query(query, (critic_id,), fetch=True)
    else:
        query = """
            SELECT id, critic_id,
                   parsed_title, parsed_short_review, parsed_full_review
            FROM pages
            WHERE status IN ('parsed', 'extracted', 'enriched')
              AND LENGTH(COALESCE(parsed_title, '')) > 0
              AND LENGTH(COALESCE(parsed_full_review, '')) > 0
        """
        candidates = local_db.execute_query(query, fetch=True)

    logger.info(f"Found {len(candidates)} candidate pages for sampling")

    if not candidates:
        raise ValueError("No candidates found for sampling")

    # Select samples
    if mode == "per_critic" and not critic_id:
        # Group by critic and sample proportionally
        by_critic = {}
        for page in candidates:
            c = page.get("critic_id") or "unknown"
            if c not in by_critic:
                by_critic[c] = []
            by_critic[c].append(page)

        logger.info(f"Stratified sampling across {len(by_critic)} critics")

        samples = []
        per_critic = max(1, size // len(by_critic))

        for c in by_critic:
            critic_samples = random.sample(by_critic[c], min(per_critic, len(by_critic[c])))
            samples.extend(critic_samples)
            if len(samples) >= size:
                samples = samples[:size]
                break

        # Fill remaining if needed
        if len(samples) < size:
            remaining = [p for p in candidates if p not in samples]
            if remaining:
                additional = random.sample(remaining, min(size - len(samples), len(remaining)))
                samples.extend(additional)

    else:
        # Random sampling across all or for specific critic
        samples = random.sample(candidates, min(size, len(candidates)))

    logger.info(f"Selected {len(samples)} samples")

    # Create batch in eval.db
    batch_id = create_sample_batch(
        sample_size=len(samples),
        critic_id=critic_id,
        mode=mode,
        population_size=len(candidates),
    )

    # Add samples to batch
    for page in samples:
        add_sample_to_batch(
            batch_id=batch_id,
            page_id=page["id"],
            critic_id=page.get("critic_id"),
            input_title=page.get("parsed_title") or "",
            input_summary=page.get("parsed_short_review") or "",
            input_full_review=page.get("parsed_full_review") or "",
        )

    logger.info(f"Created batch {batch_id} with {len(samples)} samples")
    return batch_id


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Create evaluation sample batch")
    parser.add_argument("--size", type=int, default=100, help="Number of samples to collect")
    parser.add_argument("--critic", type=str, help="Filter by critic ID (enables per_critic mode)")
    parser.add_argument("--mode", type=str, default="per_critic", choices=["per_critic", "across_all"],
                       help="Sampling mode")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    batch_id = create_sample_batch_from_db(
        size=args.size,
        critic_id=args.critic,
        mode=args.mode,
        seed=args.seed,
    )

    print(f"Created batch: {batch_id}")


if __name__ == "__main__":
    main()
