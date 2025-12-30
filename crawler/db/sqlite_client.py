"""SQLite client for local database operations."""

import sqlite3
import logging
import uuid
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "/Users/ravi/Documents/Projects/movie-review-miner/crawler/local.db"


class SQLiteClient:
    """SQLite database client for local development."""

    def __init__(self, db_path: str = DB_PATH):
        """Initialize SQLite client and create tables if needed."""
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database and create all required tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # critics table (renamed from ref_critics)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS critics (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_url TEXT,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # movies table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id TEXT PRIMARY KEY,
                title TEXT,
                release_year INTEGER,
                language TEXT,
                genre TEXT,
                popularity REAL,
                poster_path TEXT,
                tmdb_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Create indexes for movies
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_release_year ON movies(release_year)")

            # pages table (merged raw_scraped_pages + stg_clean_reviews)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                page_url TEXT UNIQUE NOT NULL,
                base_url TEXT,
                critic_id TEXT,

                page_content TEXT,
                fetched_at TIMESTAMP,

                parsed_title TEXT,
                parsed_short_review TEXT,
                parsed_full_review TEXT,
                parsed_review_date TEXT,
                parsed_at TIMESTAMP,

                is_film_review BOOLEAN,
                movie_names TEXT,
                sentiment TEXT,
                cleaned_title TEXT,
                cleaned_short_review TEXT,
                extracted_at TIMESTAMP,

                movie_id TEXT,
                enriched_at TIMESTAMP,

                status TEXT DEFAULT 'pending',
                error_type TEXT,
                error_message TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (critic_id) REFERENCES critics(id),
                FOREIGN KEY (movie_id) REFERENCES movies(id)
            )
            """)

            # Create indexes for pages
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_critic_id ON pages(critic_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_page_url ON pages(page_url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_movie_id ON pages(movie_id)")

            conn.commit()
            logger.info(f"Successfully initialized SQLite database at {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
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
                # Convert sqlite3.Row objects to dicts
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

    def execute_many(self, query: str, data: list) -> int:
        """Execute multiple inserts with a single query."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.executemany(query, data)
            conn.commit()
            logger.info(f"Successfully inserted {cursor.rowcount} rows")
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error executing batch query: {e}")
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

    def insert_many(self, table: str, records: list) -> int:
        """Batch insert multiple records."""
        if not records:
            return 0

        # Ensure all records have IDs and timestamps
        for record in records:
            if "id" not in record:
                record["id"] = str(uuid.uuid4())
            if "created_at" not in record:
                record["created_at"] = datetime.utcnow().isoformat()

        # Get column names from first record
        columns = ", ".join(records[0].keys())
        placeholders = ", ".join("?" * len(records[0]))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        # Prepare data tuples
        data = [tuple(record.values()) for record in records]

        return self.execute_many(query, data)

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
        data["updated_at"] = datetime.utcnow().isoformat()

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

    def delete(self, table: str, where: str, params: tuple = None) -> int:
        """Delete records from a table."""
        query = f"DELETE FROM {table} WHERE {where}"

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error deleting from {table}: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def upsert(self, table: str, records: list, conflict_column: str = "id") -> int:
        """Upsert records (insert or update on conflict)."""
        if not records:
            return 0

        # Ensure all records have IDs and timestamps
        for record in records:
            if "id" not in record:
                record["id"] = str(uuid.uuid4())
            if "created_at" not in record:
                record["created_at"] = datetime.utcnow().isoformat()

        columns = ", ".join(records[0].keys())
        placeholders = ", ".join("?" * len(records[0]))

        # Build the SET clause for conflict resolution
        set_clause = ", ".join([f"{k} = excluded.{k}" for k in records[0].keys() if k != conflict_column])

        query = f"""
        INSERT INTO {table} ({columns}) VALUES ({placeholders})
        ON CONFLICT({conflict_column}) DO UPDATE SET {set_clause}
        """

        data = [tuple(record.values()) for record in records]
        return self.execute_many(query, data)


# Create a singleton instance
db = SQLiteClient()
