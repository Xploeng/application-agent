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
    _migrate_status_check(Path(path))


def _schema_statements() -> list[str]:
    """schema.sql split into statements (trigger bodies contain ';')."""
    statements, buf = [], ""
    for line in SCHEMA.read_text().splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            statements.append(buf)
            buf = ""
    return statements


def _migrate_status_check(path: Path) -> None:
    """Rebuild `applications` once if its status CHECK predates to_apply/dismissed.

    SQLite cannot alter a CHECK, so: backup, rename old table, recreate from
    schema.sql, copy rows (ids kept), verify, all in one transaction.
    """
    conn = sqlite3.connect(path, timeout=5, isolation_level=None)
    try:
        (ddl,) = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'applications'").fetchone()
        if "'to_apply'" in ddl:
            return
        with sqlite3.connect(path.with_name("tracking-pre-migration.db")) as backup:
            conn.backup(backup)
        backup.close()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("PRAGMA legacy_alter_table = ON")  # keep events' FK pointing at 'applications'
        conn.execute("BEGIN IMMEDIATE")
        try:
            before = conn.execute("SELECT count(*) FROM applications").fetchone()[0]
            conn.execute("DROP TRIGGER IF EXISTS applications_status_change")
            conn.execute("ALTER TABLE applications RENAME TO applications_old")
            for statement in _schema_statements():
                conn.execute(statement)
            conn.execute("INSERT INTO applications SELECT * FROM applications_old")
            conn.execute("DROP TABLE applications_old")
            after = conn.execute("SELECT count(*) FROM applications").fetchone()[0]
            if after != before or conn.execute("PRAGMA foreign_key_check").fetchall():
                raise sqlite3.IntegrityError(f"status migration check failed ({before} -> {after} rows)")
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
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
