"""Access to the local application-tracking store (SQLite)."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "tracking.db"
SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the store with the per-connection pragmas every writer needs."""
    conn = sqlite3.connect(path, timeout=5)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init(path: Path = DB_PATH) -> None:
    """Create the store and its tables if missing; existing data is untouched."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")  # persistent in the file
        conn.executescript(SCHEMA.read_text())
    conn.close()


def run_sql(sql: str, params: list[str], path: Path = DB_PATH) -> list[tuple]:
    """Execute one statement in its own transaction; return any rows."""
    conn = connect(path)
    try:
        with conn:
            return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if sys.argv[1:2] == ["sql"] and len(sys.argv) > 2:
        # Usage: python -m tracking.db sql "<SQL with ? placeholders>" [params...]
        try:
            rows = run_sql(sys.argv[2], sys.argv[3:])
        except sqlite3.Error as e:
            sys.exit(f"SQL error: {e}")
        for row in rows:
            print("|".join("" if v is None else str(v) for v in row))
    else:
        init()
        print(f"Initialised {DB_PATH}")
