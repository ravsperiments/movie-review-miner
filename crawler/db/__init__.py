"""Database module for movie-review-miner.

Provides SQLite (local development) and Supabase (production) backends.
"""

from pathlib import Path
from crawler.db.sqlite_client import set_db_path, get_db, get_db_path


def init_test_db(seed_critics: bool = True) -> None:
    """Initialize test.db with schema and optional seed data.

    Call this to set up a fresh test database for development/testing.

    Args:
        seed_critics: If True, insert sample critic data for testing.

    Usage:
        python -c "from crawler.db import init_test_db; init_test_db()"
    """
    test_db_path = Path(__file__).parent.parent / "test.db"

    # Remove existing test.db if it exists
    if test_db_path.exists():
        test_db_path.unlink()
        print(f"Removed existing test database: {test_db_path}")

    # Set path and create fresh database
    set_db_path(test_db_path)
    db = get_db()

    print(f"Initialized test database: {test_db_path}")

    if seed_critics:
        # Insert sample critic for testing
        sample_critics = [
            {
                "id": "test-critic-baradwaj",
                "name": "Baradwaj Rangan",
                "base_url": "https://baradwajrangan.wordpress.com",
                "bio": "Test critic for development",
            }
        ]
        db.insert_many("critics", sample_critics)
        print(f"Seeded {len(sample_critics)} test critic(s)")


__all__ = ["set_db_path", "get_db", "get_db_path", "init_test_db"]
