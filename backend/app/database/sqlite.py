"""SQLite connection manager with auto-migration."""

import sqlite3
import os
from pathlib import Path
from app.config import settings


_schema_sql: str | None = None


def _load_schema() -> str:
    """Load schema.sql content, cached."""
    global _schema_sql
    if _schema_sql is not None:
        return _schema_sql

    schema_path = Path(__file__).parent / "schema.sql"
    _schema_sql = schema_path.read_text(encoding="utf-8")
    return _schema_sql


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and foreign keys enabled."""
    db_path = settings.db_path

    if db_path == ":memory:" or db_path.startswith("file:"):
        conn = sqlite3.connect(db_path, uri=True, check_same_thread=False)
    else:
        db_file = Path(db_path)
        if not db_file.is_absolute():
            db_file = Path.cwd() / db_file
        db_file.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_file), check_same_thread=False)

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Run schema migration on startup.

    Creates tables if not exist, then applies incremental migrations
    for new columns added after initial schema.
    """
    conn = get_connection()
    try:
        schema = _load_schema()
        conn.executescript(schema)
        conn.commit()

        # Incremental migrations for V2 chunk metadata
        _migrate_v2_chunk_metadata(conn)
    finally:
        conn.close()


def _migrate_v2_chunk_metadata(conn: sqlite3.Connection) -> None:
    """Add V2 chunk metadata columns if they don't exist (idempotent)."""
    migrations = [
        "ALTER TABLE chunks ADD COLUMN section_path TEXT DEFAULT ''",
        "ALTER TABLE chunks ADD COLUMN heading_level INTEGER DEFAULT 0",
        "ALTER TABLE chunks ADD COLUMN prev_chunk_id TEXT DEFAULT NULL",
        "ALTER TABLE chunks ADD COLUMN next_chunk_id TEXT DEFAULT NULL",
    ]
    # SQLite only reports the first missing column via error; we try each.
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists — skip
            pass


# Application-wide connection pool (single connection for SQLite is fine for MVP)
_connection: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Get or create the shared database connection."""
    global _connection
    if _connection is None:
        _connection = get_connection()
    return _connection


def close_db() -> None:
    """Close the shared database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
