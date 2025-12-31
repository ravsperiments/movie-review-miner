"""Eval database client for evaluation results storage.

Uses a separate eval.db file to store sample batches, LLM outputs, and judge scores.
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from review_aggregator.utils.logger import get_logger

logger = get_logger(__name__)

# Eval database path (separate from local.db)
EVAL_DB_PATH = Path(__file__).parent.parent.parent / "data" / "eval.db"

# Module-level singleton
_eval_db_instance: "EvalDB | None" = None


def get_eval_db() -> "EvalDB":
    """Get the eval database client singleton."""
    global _eval_db_instance
    if _eval_db_instance is None:
        _eval_db_instance = EvalDB(str(EVAL_DB_PATH))
    return _eval_db_instance


class EvalDB:
    """SQLite database client for evaluation data."""

    def __init__(self, db_path: str | None = None):
        """Initialize eval DB client and create tables."""
        self.db_path = db_path if db_path else str(EVAL_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database with eval tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # sample_batches table - tracks evaluation batches
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sample_batches (
                id TEXT PRIMARY KEY,
                critic_id TEXT,
                population_size INTEGER,
                sample_size INTEGER,
                sample_mode TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # samples table - individual samples in a batch
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                page_id TEXT NOT NULL,
                critic_id TEXT,
                input_title TEXT,
                input_summary TEXT,
                input_full_review TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES sample_batches(id)
            )
            """)

            # llm_outputs table - model outputs for samples
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_outputs (
                id TEXT PRIMARY KEY,
                sample_id TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                output_is_film_review BOOLEAN,
                output_movie_names TEXT,
                output_sentiment TEXT,
                output_cleaned_title TEXT,
                output_cleaned_short_review TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost_usd REAL,
                latency_ms REAL,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sample_id) REFERENCES samples(id)
            )
            """)

            # judge_scores table - judge evaluations of outputs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS judge_scores (
                id TEXT PRIMARY KEY,
                llm_output_id TEXT NOT NULL,
                judge_model TEXT NOT NULL,
                score_is_film_review INTEGER,
                score_movie_names INTEGER,
                score_sentiment INTEGER,
                score_cleaned_title INTEGER,
                score_cleaned_short_review INTEGER,
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (llm_output_id) REFERENCES llm_outputs(id)
            )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_batch_id ON samples(batch_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_page_id ON samples(page_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_outputs_sample_id ON llm_outputs(sample_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_outputs_model ON llm_outputs(model)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_judge_scores_llm_output_id ON judge_scores(llm_output_id)")

            conn.commit()
            logger.info(f"Initialized eval database at {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing eval database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """Execute a query and optionally fetch results."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch:
                result = cursor.fetchall()
                return [dict(row) for row in result]
            else:
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def insert(self, table: str, data: dict) -> str:
        """Insert a single record and return the ID."""
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow().isoformat()

        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query, tuple(data.values()))
            conn.commit()
            return data["id"]
        except Exception as e:
            logger.error(f"Error inserting into {table}: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def select(self, table: str, columns: str = "*", where: str = None, params: tuple = None, limit: int = None) -> list:
        """Select records from a table."""
        query = f"SELECT {columns} FROM {table}"
        if where:
            query += f" WHERE {where}"
        if limit:
            query += f" LIMIT {limit}"

        return self.execute_query(query, params, fetch=True)

    def update(self, table: str, data: dict, where: str, params: tuple = None) -> int:
        """Update records in a table."""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            update_params = tuple(data.values())
            if params:
                update_params = update_params + params
            cursor.execute(query, update_params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error updating {table}: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()


# Query functions for batch operations

def create_sample_batch(
    sample_size: int,
    critic_id: str = None,
    mode: str = "per_critic",
    population_size: int = None,
) -> str:
    """Create a new sample batch and return its ID."""
    batch_id = str(uuid.uuid4())
    db = get_eval_db()

    db.insert("sample_batches", {
        "id": batch_id,
        "critic_id": critic_id,
        "sample_size": sample_size,
        "population_size": population_size or 0,
        "sample_mode": mode,
    })

    return batch_id


def add_sample_to_batch(
    batch_id: str,
    page_id: str,
    critic_id: str,
    input_title: str,
    input_summary: str,
    input_full_review: str,
) -> str:
    """Add a sample to a batch."""
    sample_id = str(uuid.uuid4())
    db = get_eval_db()

    db.insert("samples", {
        "id": sample_id,
        "batch_id": batch_id,
        "page_id": page_id,
        "critic_id": critic_id,
        "input_title": input_title,
        "input_summary": input_summary,
        "input_full_review": input_full_review,
    })

    return sample_id


def save_llm_output(
    sample_id: str,
    model: str,
    prompt_version: str,
    output_is_film_review: bool = None,
    output_movie_names: str = None,
    output_sentiment: str = None,
    output_cleaned_title: str = None,
    output_cleaned_short_review: str = None,
    input_tokens: int = None,
    output_tokens: int = None,
    cost_usd: float = None,
    latency_ms: float = None,
    error: str = None,
) -> str:
    """Save LLM output for a sample."""
    output_id = str(uuid.uuid4())
    db = get_eval_db()

    db.insert("llm_outputs", {
        "id": output_id,
        "sample_id": sample_id,
        "model": model,
        "prompt_version": prompt_version,
        "output_is_film_review": output_is_film_review,
        "output_movie_names": output_movie_names,
        "output_sentiment": output_sentiment,
        "output_cleaned_title": output_cleaned_title,
        "output_cleaned_short_review": output_cleaned_short_review,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
        "error": error,
    })

    return output_id


def save_judge_score(
    llm_output_id: str,
    judge_model: str,
    score_is_film_review: int,
    score_movie_names: int,
    score_sentiment: int,
    score_cleaned_title: int,
    score_cleaned_short_review: int,
    reasoning: str = None,
) -> str:
    """Save judge score for an LLM output."""
    score_id = str(uuid.uuid4())
    db = get_eval_db()

    db.insert("judge_scores", {
        "id": score_id,
        "llm_output_id": llm_output_id,
        "judge_model": judge_model,
        "score_is_film_review": score_is_film_review,
        "score_movie_names": score_movie_names,
        "score_sentiment": score_sentiment,
        "score_cleaned_title": score_cleaned_title,
        "score_cleaned_short_review": score_cleaned_short_review,
        "reasoning": reasoning,
    })

    return score_id


def get_latest_batch(critic_id: str = None) -> dict | None:
    """Get the most recent batch."""
    db = get_eval_db()

    if critic_id:
        results = db.select(
            "sample_batches",
            where="critic_id = ?",
            params=(critic_id,),
            limit=1
        )
    else:
        query = "SELECT * FROM sample_batches ORDER BY created_at DESC LIMIT 1"
        results = db.execute_query(query, fetch=True)

    return results[0] if results else None


def get_batch(batch_id: str) -> dict | None:
    """Get a specific batch by ID."""
    db = get_eval_db()
    results = db.select("sample_batches", where="id = ?", params=(batch_id,), limit=1)
    return results[0] if results else None


def get_samples(batch_id: str) -> list[dict]:
    """Get all samples in a batch."""
    db = get_eval_db()
    return db.select("samples", where="batch_id = ?", params=(batch_id,))


def get_sample(sample_id: str) -> dict | None:
    """Get a specific sample by ID."""
    db = get_eval_db()
    results = db.select("samples", where="id = ?", params=(sample_id,), limit=1)
    return results[0] if results else None


def get_llm_outputs(sample_id: str = None, batch_id: str = None) -> list[dict]:
    """Get LLM outputs, optionally filtered."""
    db = get_eval_db()

    if sample_id:
        return db.select("llm_outputs", where="sample_id = ?", params=(sample_id,))
    elif batch_id:
        # Join with samples table to filter by batch
        query = """
            SELECT lo.* FROM llm_outputs lo
            JOIN samples s ON lo.sample_id = s.id
            WHERE s.batch_id = ?
        """
        return db.execute_query(query, (batch_id,), fetch=True)
    else:
        return db.select("llm_outputs")


def get_unscored_outputs(batch_id: str = None) -> list[dict]:
    """Get LLM outputs that haven't been scored yet."""
    db = get_eval_db()

    if batch_id:
        query = """
            SELECT lo.* FROM llm_outputs lo
            JOIN samples s ON lo.sample_id = s.id
            WHERE s.batch_id = ? AND lo.id NOT IN (
                SELECT DISTINCT llm_output_id FROM judge_scores
            )
        """
        return db.execute_query(query, (batch_id,), fetch=True)
    else:
        query = """
            SELECT * FROM llm_outputs
            WHERE id NOT IN (
                SELECT DISTINCT llm_output_id FROM judge_scores
            )
        """
        return db.execute_query(query, fetch=True)


def get_judge_scores(llm_output_id: str = None) -> list[dict]:
    """Get judge scores for an output."""
    db = get_eval_db()

    if llm_output_id:
        return db.select("judge_scores", where="llm_output_id = ?", params=(llm_output_id,))
    else:
        return db.select("judge_scores")


def get_batch_stats(batch_id: str) -> dict:
    """Get evaluation statistics for a batch."""
    db = get_eval_db()

    # Get batch info
    batch = get_batch(batch_id)
    if not batch:
        return None

    # Count samples
    samples = get_samples(batch_id)
    sample_count = len(samples)

    # Get outputs for batch
    outputs = get_llm_outputs(batch_id=batch_id)

    # Count by model
    model_counts = {}
    for output in outputs:
        model = output["model"]
        model_counts[model] = model_counts.get(model, 0) + 1

    # Get scores for outputs
    output_ids = [o["id"] for o in outputs]
    all_scores = []
    for output_id in output_ids:
        scores = get_judge_scores(output_id)
        all_scores.extend(scores)

    # Calculate field accuracy (pass if ALL judges score 1)
    field_accuracy = {}
    for field in ["is_film_review", "movie_names", "sentiment", "cleaned_title", "cleaned_short_review"]:
        field_key = f"score_{field}"
        if all_scores:
            passes = sum(1 for s in all_scores if s.get(field_key) == 1)
            total_judges = len(set(s["judge_model"] for s in all_scores))
            total_outputs = len(output_ids)
            if total_judges > 0 and total_outputs > 0:
                # Field passes if all judges scored it as 1 for all outputs
                field_accuracy[field] = passes / (total_judges * total_outputs)
            else:
                field_accuracy[field] = 0.0
        else:
            field_accuracy[field] = 0.0

    return {
        **batch,
        "sample_count": sample_count,
        "output_count": len(outputs),
        "score_count": len(all_scores),
        "model_counts": model_counts,
        "field_accuracy": field_accuracy,
    }
