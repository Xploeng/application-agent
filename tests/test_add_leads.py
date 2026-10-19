import json
import tempfile
import unittest
from pathlib import Path

from jobs.add_leads import add_leads
from tracking.db import connect, init


class AddLeadsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = root / "t.db"
        init(self.db)
        self.run = root / "run"
        self.run.mkdir()
        jobs = [{"id": "j1", "source": "indeed", "title": "AI Engineer", "company": "Acme", "location": "München",
                 "date": "2026-10-15", "url": "https://de.indeed.com/viewjob?jk=a"},
                {"id": "j2", "source": "linkedin", "title": "RL Engineer", "company": "Beta", "location": None,
                 "date": None, "url": "https://jobs.lever.co/beta/1"},
                {"id": "j3", "source": "google", "title": "ML Eng", "company": "Gamma", "location": None,
                 "date": None, "url": "https://x/3"}]
        (self.run / "jobs.json").write_text(json.dumps(jobs))
        (self.run / "j1.txt").write_text("Full posting text")
        (self.run / "j2.txt").write_text("")
        (self.run / "j3.txt").write_text("Gamma text")

    def tearDown(self):
        self.tmp.cleanup()

    def test_inserts_leads_with_text_and_reason(self):
        added, skipped = add_leads(self.run, [{"id": "j1", "reason": "agentic team"}, {"id": "j2", "reason": "RL"},
                                              {"id": "j9", "reason": "?"}], self.db)
        self.assertEqual((added, skipped), (2, ["j9: unknown id"]))
        conn = connect(self.db)
        try:
            rows = conn.execute("SELECT company, role, status, source, url, posting_text, posting_captured_at IS NOT NULL "
                                "FROM applications ORDER BY id").fetchall()
            self.assertEqual(rows, [("Acme", "AI Engineer", "lead", "indeed", "https://de.indeed.com/viewjob?jk=a",
                                     "Full posting text", 1),
                                    ("Beta", "RL Engineer", "lead", "linkedin", "https://jobs.lever.co/beta/1", None, 0)])
            self.assertEqual(conn.execute("SELECT detail, source FROM events WHERE kind = 'note' ORDER BY id").fetchall(),
                             [("agentic team", "evaluator"), ("RL", "evaluator")])
        finally:
            conn.close()

    def test_already_tracked_url_is_skipped(self):
        add_leads(self.run, [{"id": "j3", "reason": "x"}], self.db)
        added, skipped = add_leads(self.run, [{"id": "j3", "reason": "x"}], self.db)
        self.assertEqual((added, skipped), (0, ["j3: already tracked"]))


if __name__ == "__main__":
    unittest.main()
