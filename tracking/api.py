"""Local web UI backend: read the tracking store, apply batched lead reviews.

Run: uv run python -m tracking.api  (serves web/dist on http://127.0.0.1:8765)
"""

import sqlite3
import tomllib
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from tracking.db import DB_PATH, ROOT, connect

PREFS_PATH = ROOT / "data" / "preferences.toml"
DIST = ROOT / "web" / "dist"
HOST, PORT = "127.0.0.1", 8765
NEW_STATUS = {"apply": "to_apply", "dismiss": "dismissed"}

DETAIL_SQL = """
SELECT a.id, a.company, a.role, a.status, a.url, a.location, a.source, a.posting_captured_at, a.posting_text,
       (SELECT detail FROM events e WHERE e.application_id = a.id AND e.kind = 'note' AND e.source = 'evaluator'
        ORDER BY e.id DESC LIMIT 1) AS evaluator_reason
FROM applications a WHERE a.id = ?"""


class Decision(BaseModel):
    id: int
    decision: Literal["apply", "dismiss"]  # a skip never writes anything, so it is never sent
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def blank_is_none(cls, v: str | None) -> str | None:
        return (v or "").strip() or None


class Batch(BaseModel):
    decisions: list[Decision]

    @model_validator(mode="after")
    def unique_ids(self) -> "Batch":
        ids = [d.id for d in self.decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate application ids")
        return self


def _rows(db: Path, sql: str, params: tuple = ()) -> list[dict]:
    conn = connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def _reasons(prefs: Path) -> list[str]:
    try:
        with prefs.open("rb") as f:
            return [str(r) for r in tomllib.load(f).get("review", {}).get("reasons", [])]
    except FileNotFoundError:
        return []


def apply_batch(db: Path, decisions: list[Decision]) -> dict:
    """Write all decisions in one transaction; leads no longer `lead` are conflicts, not errors."""
    conn = connect(db)
    conn.isolation_level = None  # explicit BEGIN IMMEDIATE: take the write lock up front
    counts, conflicts = {"to_apply": 0, "dismissed": 0, "notes": 0}, []
    try:
        conn.execute("BEGIN IMMEDIATE")
        for d in decisions:
            if not conn.execute("UPDATE applications SET status = ? WHERE id = ? AND status = 'lead'",
                                (NEW_STATUS[d.decision], d.id)).rowcount:
                conflicts.append(d.id)
                continue
            counts[NEW_STATUS[d.decision]] += 1
            if d.reason:
                conn.execute("INSERT INTO events (application_id, kind, detail, source) VALUES (?, 'note', ?, 'review')",
                             (d.id, d.reason))
                counts["notes"] += 1
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {"applied": counts, "conflicts": conflicts}


def create_app(db_path: Path = DB_PATH, prefs_path: Path = PREFS_PATH, dist: Path = DIST) -> FastAPI:
    app = FastAPI(title="Application tracking")
    # Rejects DNS-rebinding pages; uvicorn binding to 127.0.0.1 keeps other machines out.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.get("/api/applications")
    def applications() -> list[dict]:
        return _rows(db_path, "SELECT id, company, role, status, url FROM applications ORDER BY id DESC")

    @app.get("/api/applications/{app_id}")
    def application(app_id: int) -> dict:
        rows = _rows(db_path, DETAIL_SQL, (app_id,))
        if not rows:
            raise HTTPException(404, "No such application")
        return rows[0]

    @app.get("/api/review")
    def review_queue() -> dict:
        ids = _rows(db_path, "SELECT id FROM applications WHERE status = 'lead' ORDER BY id")
        return {"lead_ids": [r["id"] for r in ids], "reasons": _reasons(prefs_path)}

    @app.post("/api/review")
    def review(batch: Batch) -> dict:
        try:
            return apply_batch(db_path, batch.decisions)
        except sqlite3.OperationalError as e:
            if "locked" not in str(e):
                raise
            raise HTTPException(503, "The tracking DB is busy. Nothing was written; your decisions are still pending.")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist.resolve()):
            return FileResponse(file)
        if not (dist / "index.html").exists():
            return PlainTextResponse("UI not built: run `pnpm --dir web build`, then reload.")
        return FileResponse(dist / "index.html")  # client-side routes like /review

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
