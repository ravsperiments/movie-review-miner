import sqlite3
from typing import Dict, List, Tuple

DB_PATH = "reviews.db"


def init_db(db_path: str = DB_PATH) -> None:
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


def save_post(post: Dict[str, str], db_path: str = DB_PATH) -> None:
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


def update_recommendation(link: str, recommendation: str, db_path: str = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE posts SET recommendation=? WHERE link=?",
            (recommendation, link),
        )
        conn.commit()


def fetch_unanalyzed(db_path: str = DB_PATH) -> List[Tuple[str, str]]:
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT link, full_review FROM posts WHERE recommendation IS NULL"
        )
        return cur.fetchall()

