"""
database.py — SQLite connection and parameterized query helpers.

Design decisions (per assignment requirements):
- Direct parameterized SQL queries — no ORM.
- Never concatenate untrusted input into SQL.
- DB file is local (not network-reachable); only the backend process can access it.
- Thread-safe connection via check_same_thread=False + WAL mode for concurrent reads.
"""
import sqlite3
import threading
from pathlib import Path
from app.config import get_settings

# ── Module-level connection (one per thread via threading.local) ──────────────
_local = threading.local()
_DB_PATH: Path | None = None


def _get_db_path() -> Path:
    """Resolve and cache the SQLite file path from settings."""
    global _DB_PATH
    if _DB_PATH is None:
        settings = get_settings()
        # Strip the "sqlite:///" prefix if present
        url = settings.database_url
        raw_path = url.replace("sqlite:///", "")
        _DB_PATH = Path(raw_path).resolve()
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return _DB_PATH


def get_connection() -> sqlite3.Connection:
    """
    Return a thread-local SQLite connection.
    Creates the connection on first access per thread.
    WAL mode allows concurrent reads while a write is in progress.
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        db_path = _get_db_path()
        _local.conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        _local.conn.row_factory = sqlite3.Row  # rows accessible by column name
        _local.conn.execute("PRAGMA journal_mode=WAL;")
        _local.conn.execute("PRAGMA foreign_keys=ON;")
    return _local.conn


def close_connection() -> None:
    """Close the thread-local connection (call at app shutdown)."""
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """
    Execute a single parameterized statement.
    ALWAYS use this — never format SQL with user input.
    """
    conn = get_connection()
    return conn.execute(sql, params)


def executemany(sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
    """Execute a parameterized statement for multiple rows."""
    conn = get_connection()
    return conn.executemany(sql, params_list)


def fetchall(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Execute and return all rows."""
    return execute(sql, params).fetchall()


def fetchone(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Execute and return one row or None."""
    return execute(sql, params).fetchone()


def commit() -> None:
    """Commit the current transaction."""
    get_connection().commit()


def rollback() -> None:
    """Roll back any uncommitted writes after a collector error."""
    get_connection().rollback()


def init_db() -> None:
    """
    Create all tables from schema.sql if they don't exist.
    Called once at application startup.
    """
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    schema_sql = schema_path.read_text(encoding="utf-8")
    conn = get_connection()
    conn.executescript(schema_sql)
    # Additive migration for databases created before ticker stale-state tracking.
    ticker_columns = {row["name"] for row in conn.execute("PRAGMA table_info(ticker_snapshots)")}
    if "is_stale" not in ticker_columns:
        # Existing quotes predate the stale flag, so their freshness cannot be assumed.
        conn.execute("ALTER TABLE ticker_snapshots ADD COLUMN is_stale INTEGER NOT NULL DEFAULT 1")
    conn.commit()
