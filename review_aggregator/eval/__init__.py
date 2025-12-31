"""Simplified evaluation system for review processing pipeline.

Components:
- sampler: Create sample batches from parsed pages
- runner: Run models on sample batches
- judge: Judge panel scoring of model outputs
- view: HTML export of evaluation results
- db: SQLite storage for eval data (eval.db)

Usage:
    # 1. Create sample batch
    python -m review_aggregator.eval.sampler --size 100 --critic baradwajrangan

    # 2. Run models on batch
    python -m review_aggregator.eval.runner --models anthropic/claude-sonnet-4-20250514 --batch latest

    # 3. Score outputs with judges
    python -m review_aggregator.eval.judge --batch latest --judges anthropic/claude-sonnet-4-20250514

    # 4. Export results to HTML
    python -m review_aggregator.eval.view <batch_id>
"""

from .db import (
    get_eval_db,
    create_sample_batch,
    add_sample_to_batch,
    save_llm_output,
    save_judge_score,
    get_latest_batch,
    get_batch,
    get_samples,
    get_batch_stats,
)
from .sampler import create_sample_batch_from_db
from .model_runner import run_eval, get_critic_prompt
from .judge import score_outputs

__all__ = [
    # DB operations
    "get_eval_db",
    "create_sample_batch",
    "add_sample_to_batch",
    "save_llm_output",
    "save_judge_score",
    "get_latest_batch",
    "get_batch",
    "get_samples",
    "get_batch_stats",
    # Sampler
    "create_sample_batch_from_db",
    # Runner
    "run_eval",
    "get_critic_prompt",
    # Judge
    "score_outputs",
]
