"""Print schema-only diagnostics; never inspect rows or credential material."""
import sqlite3
from pathlib import Path

from app.config import get_settings

url = get_settings().database_url
if not url.startswith("sqlite:///"):
    raise SystemExit("This helper supports SQLite only.")
database_path = Path(url.removeprefix("sqlite:///"))
if not database_path.is_absolute():
    database_path = Path(__file__).parent / database_path
if not database_path.is_file():
    raise SystemExit("Configured database file does not exist.")

with sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True) as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    print("Database schema tables:")
    for (name,) in tables:
        print(f"- {name}")
