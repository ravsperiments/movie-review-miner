"""SQLite helpers used for local persistence during development."""

import sqlite3
from typing import Dict, List, Tuple

from utils.logger import get_logger

# Path to the SQLite database file
DB_PATH = "reviews.db"

# Module level logger for DB operations
logger = get_logger(__name__)


def init_db(db_path: str = DB_PATH) -> None:
    """Create the SQLite schema if it does not already exist."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            link TEXT PRIMARY KEY,
            date TEXT,
            title TEXT,
            reviewer TEXT,
            subtext TEXT,
            full_review TEXT,
            recommendation TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    logger.debug("Database initialised at %s", db_path)


def save_post(post: Dict[str, str], db_path: str = DB_PATH) -> None:
    """Insert a new post record if it does not already exist."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO posts (
                link,
                date,
                title,
                reviewer,
                subtext,
                full_review,
                recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.get("link"),
                post.get("date"),
                post.get("title"),
                post.get("reviewer"),
                post.get("subtext"),
                post.get("full_review"),
                post.get("recommendation"),
            ),
        )
        conn.commit()
    logger.debug("Saved post to %s", db_path)


def update_recommendation(link: str, recommendation: str, db_path: str = DB_PATH) -> None:
    """Update the sentiment field for a previously stored post."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE posts SET recommendation=? WHERE link=?",
            (recommendation, link),
        )
        conn.commit()
    logger.debug("Updated recommendation for %s", link)


def fetch_unanalyzed(db_path: str = DB_PATH) -> List[Tuple[str, str]]:
    """Return posts that still need sentiment analysis."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT link, full_review FROM posts WHERE recommendation IS NULL"
        )
        rows = cur.fetchall()
        logger.debug("Fetched %d unanalyzed posts", len(rows))
        return rows

