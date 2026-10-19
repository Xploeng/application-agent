import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tracking.api import create_app
from tracking.db import connect, init


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db, self.prefs, self.dist = root / "t.db", root / "prefs.toml", root / "dist"
        init(self.db)
        self.ids = [self.add("Acme", "lead", "https://a"), self.add("Beta", "lead"), self.add("Gamma", "lead"),
                    self.add("Delta", "applied")]
        with connect(self.db) as conn:
            conn.executemany("INSERT INTO events (application_id, kind, detail, source) VALUES (?, 'note', ?, ?)",
                             [(self.ids[0], "old reason", "evaluator"), (self.ids[0], "agentic team", "evaluator"),
                              (self.ids[0], "user note", "review")])
        conn.close()
        self.client = TestClient(create_app(self.db, self.prefs, self.dist), base_url="http://127.0.0.1")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, company, status, url=None):
        with connect(self.db) as conn:
            new_id = conn.execute("INSERT INTO applications (company, role, status, url, posting_text) "
                                  "VALUES (?, 'ML Engineer', ?, ?, '## Tasks')", (company, status, url)).lastrowid
        conn.close()
        return new_id

    def query(self, sql, params=()):
        with connect(self.db) as conn:
            rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def post(self, decisions):
        return self.client.post("/api/review", json={"decisions": decisions})

    # read endpoints

    def test_list(self):
        rows = self.client.get("/api/applications").json()
        self.assertEqual(len(rows), 4)
        self.assertEqual(set(rows[0]), {"id", "company", "role", "status", "url"})

    def test_detail_has_latest_evaluator_reason(self):
        row = self.client.get(f"/api/applications/{self.ids[0]}").json()
        self.assertEqual((row["company"], row["evaluator_reason"], row["posting_text"]), ("Acme", "agentic team", "## Tasks"))
        self.assertEqual(self.client.get("/api/applications/999").status_code, 404)

    def test_review_queue_and_reasons(self):
        self.prefs.write_text('[search]\nterms = []\n[review]\nreasons = ["consulting", "too senior"]\n')
        self.assertEqual(self.client.get("/api/review").json(),
                         {"lead_ids": self.ids[:3], "reasons": ["consulting", "too senior"]})

    def test_reasons_empty_without_file_or_section(self):
        self.assertEqual(self.client.get("/api/review").json()["reasons"], [])
        self.prefs.write_text("[search]\nterms = []\n")
        self.assertEqual(self.client.get("/api/review").json()["reasons"], [])

    # applying decisions

    def test_mixed_batch(self):
        a, b, c = self.ids[:3]
        r = self.post([{"id": a, "decision": "apply", "reason": "remote ok"},
                       {"id": b, "decision": "dismiss", "reason": " consulting "}, {"id": c, "decision": "dismiss"}])
        self.assertEqual(r.json(), {"applied": {"to_apply": 1, "dismissed": 2, "notes": 2}, "conflicts": []})
        self.assertEqual(self.query("SELECT status FROM applications WHERE id IN (?, ?, ?) ORDER BY id", (a, b, c)),
                         [("to_apply",), ("dismissed",), ("dismissed",)])
        self.assertEqual(self.query("SELECT application_id, detail FROM events WHERE source = 'review' AND detail != 'user note'"
                                    " ORDER BY id"), [(a, "remote ok"), (b, "consulting")])

    def test_blank_reason_adds_no_note(self):
        r = self.post([{"id": self.ids[0], "decision": "dismiss", "reason": "  "}])
        self.assertEqual(r.json()["applied"], {"to_apply": 0, "dismissed": 1, "notes": 0})
        self.assertEqual(self.query("SELECT count(*) FROM events WHERE kind = 'note' AND application_id = ?",
                                    (self.ids[0],)), [(3,)])

    def test_changed_lead_is_conflict(self):
        a, b = self.ids[:2]
        with connect(self.db) as conn:
            conn.execute("UPDATE applications SET status = 'applied' WHERE id = ?", (a,))
        conn.close()
        r = self.post([{"id": a, "decision": "dismiss", "reason": "nope"}, {"id": b, "decision": "apply"},
                       {"id": self.ids[3], "decision": "apply", "reason": "x"}])
        self.assertEqual(r.json(), {"applied": {"to_apply": 1, "dismissed": 0, "notes": 0},
                                    "conflicts": [a, self.ids[3]]})
        self.assertEqual(self.query("SELECT status FROM applications WHERE id = ?", (a,)), [("applied",)])
        self.assertEqual(self.query("SELECT count(*) FROM events WHERE detail IN ('nope', 'x')"), [(0,)])

    def test_invalid_batches_rejected(self):
        a = self.ids[0]
        self.assertEqual(self.post([{"id": a, "decision": "apply"}, {"id": a, "decision": "dismiss"}]).status_code, 422)
        self.assertEqual(self.post([{"id": a, "decision": "skip"}]).status_code, 422)  # skips are never sent
        self.assertEqual(self.query("SELECT status FROM applications WHERE id = ?", (a,)), [("lead",)])

    def test_non_json_body_rejected(self):
        body = '{"decisions": [{"id": %d, "decision": "dismiss"}]}' % self.ids[0]
        for ctype in ("text/plain", "application/x-www-form-urlencoded"):
            r = self.client.post("/api/review", content=body, headers={"Content-Type": ctype})
            self.assertEqual(r.status_code, 422, ctype)
        self.assertEqual(self.query("SELECT status FROM applications WHERE id = ?", (self.ids[0],)), [("lead",)])

    def test_locked_db_returns_503_and_writes_nothing(self):
        blocker = sqlite3.connect(self.db, isolation_level=None)
        blocker.execute("BEGIN IMMEDIATE")
        try:
            r = self.post([{"id": self.ids[0], "decision": "apply"}])  # waits out the 5 s busy timeout
        finally:
            blocker.execute("ROLLBACK")
            blocker.close()
        self.assertEqual(r.status_code, 503)
        self.assertEqual(self.query("SELECT status FROM applications WHERE id = ?", (self.ids[0],)), [("lead",)])

    # hardening and serving

    def test_foreign_host_rejected(self):
        evil = TestClient(create_app(self.db, self.prefs, self.dist), base_url="http://evil.example")
        r = evil.get("/api/applications")
        self.assertEqual(r.status_code, 400)
        self.assertNotIn("Acme", r.text)
        localhost = TestClient(create_app(self.db, self.prefs, self.dist), base_url="http://localhost:8765")
        self.assertEqual(localhost.get("/api/applications").status_code, 200)

    def test_frontend_serving(self):
        self.assertIn("pnpm --dir web build", self.client.get("/review").text)
        (self.dist / "assets").mkdir(parents=True)
        (self.dist / "index.html").write_text("<div id=root>")
        (self.dist / "assets" / "app.js").write_text("console.log(1)")
        self.assertEqual(self.client.get("/review").text, "<div id=root>")
        self.assertEqual(self.client.get("/app/12").text, "<div id=root>")
        self.assertEqual(self.client.get("/assets/app.js").text, "console.log(1)")
        self.assertEqual(self.client.get("/api/nope").status_code, 404)


if __name__ == "__main__":
    unittest.main()
