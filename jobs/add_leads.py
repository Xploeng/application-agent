"""Insert the job-evaluator's kept postings as leads.

Usage: echo '[{"id": "j3", "reason": "..."}]' | uv run jobs/add_leads.py <run dir>

Posting text goes straight from <run dir>/<id>.txt into the DB, so it never
passes through the main session. Each lead gets an 'evaluator' note with the reason.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tracking.db import DB_PATH, connect  # noqa: E402


def add_leads(run_dir: Path, kept: list[dict], db_path: Path = DB_PATH) -> tuple[int, list[str]]:
    jobs = {j["id"]: j for j in json.loads((run_dir / "jobs.json").read_text())}
    added, skipped = 0, []
    conn = connect(db_path)
    try:
        with conn:  # one transaction for the whole batch
            for item in kept:
                job = jobs.get(item.get("id"))
                if job is None or not job["title"]:
                    skipped.append(f"{item.get('id')}: unknown id")
                    continue
                if conn.execute("SELECT 1 FROM applications WHERE url = ?", (job["url"],)).fetchone():
                    skipped.append(f"{item['id']}: already tracked")
                    continue
                text = (run_dir / f"{item['id']}.txt").read_text().strip() or None
                app_id = conn.execute(
                    "INSERT INTO applications (company, role, location, url, source, status, posting_text, posting_captured_at) "
                    "VALUES (?, ?, ?, ?, ?, 'lead', ?, CASE WHEN ? IS NULL THEN NULL ELSE strftime('%Y-%m-%dT%H:%M:%S','now') END)",
                    (job["company"] or "unknown", job["title"], job["location"], job["url"], job["source"], text, text),
                ).lastrowid
                conn.execute("INSERT INTO events (application_id, kind, detail, source) VALUES (?, 'note', ?, 'evaluator')",
                             (app_id, item.get("reason") or ""))
                added += 1
    finally:
        conn.close()
    return added, skipped


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: echo '<json>' | uv run jobs/add_leads.py <run dir>")
    added, skipped = add_leads(Path(sys.argv[1]), json.load(sys.stdin))
    print(f"added: {added}")
    for s in skipped:
        print(f"skipped {s}")
