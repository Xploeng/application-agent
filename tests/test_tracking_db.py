import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tracking.db import connect, init


class TrackingDbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "tracking.db"
        init(self.path)
        self.conn = connect(self.path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def add(self, conn=None, **fields):
        fields = {"company": "Acme", "role": "Engineer", **fields}
        cols = ", ".join(fields)
        marks = ", ".join("?" * len(fields))
        with conn or self.conn as c:
            return c.execute(f"INSERT INTO applications ({cols}) VALUES ({marks})", tuple(fields.values())).lastrowid

    def events(self, app_id, kind="status_change"):
        return self.conn.execute(
            "SELECT detail FROM events WHERE application_id = ? AND kind = ?", (app_id, kind)
        ).fetchall()

    def test_reinit_keeps_rows(self):
        self.add()
        init(self.path)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM applications").fetchone()[0], 1)

    def test_company_and_role_required(self):
        for missing in ("company", "role"):
            with self.subTest(missing=missing), self.assertRaises(sqlite3.IntegrityError):
                self.add(**{missing: None})

    def test_duplicate_url_rejected_but_null_urls_allowed(self):
        self.add(url="https://example.com/job/1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.add(url="https://example.com/job/1")
        self.add()
        self.add()
        self.assertEqual(self.conn.execute("SELECT count(*) FROM applications").fetchone()[0], 3)

    def test_invalid_status_rejected_and_previous_kept(self):
        app = self.add(status="applied")
        with self.assertRaises(sqlite3.IntegrityError), self.conn:
            self.conn.execute("UPDATE applications SET status = 'rejectd' WHERE id = ?", (app,))
        self.assertEqual(self.conn.execute("SELECT status FROM applications WHERE id = ?", (app,)).fetchone()[0], "applied")

    def test_default_status_is_lead_and_posting_optional(self):
        app = self.add()
        row = self.conn.execute(
            "SELECT status, posting_text, posting_captured_at FROM applications WHERE id = ?", (app,)
        ).fetchone()
        self.assertEqual(row, ("lead", None, None))

    def test_status_change_logs_one_event(self):
        app = self.add(status="applied")
        with self.conn:
            self.conn.execute("UPDATE applications SET status = 'rejected' WHERE id = ?", (app,))
        self.assertEqual(self.events(app), [("applied -> rejected",)])

    def test_same_status_logs_nothing(self):
        app = self.add(status="applied")
        with self.conn:
            self.conn.execute("UPDATE applications SET status = 'applied', notes = 'x' WHERE id = ?", (app,))
        self.assertEqual(self.events(app), [])

    def test_event_for_unknown_application_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError), self.conn:
            self.conn.execute("INSERT INTO events (application_id, kind) VALUES (999, 'note')")

    def test_concurrent_writers_both_commit(self):
        self.conn.execute("BEGIN IMMEDIATE")  # hold the write lock
        self.conn.execute("INSERT INTO applications (company, role) VALUES ('A', 'r')")
        errors = []

        def second_writer():
            other = connect(self.path)
            try:
                self.add(conn=other, company="B")
            except Exception as e:
                errors.append(e)
            finally:
                other.close()

        t = threading.Thread(target=second_writer)
        t.start()
        time.sleep(0.3)  # second writer is now waiting on the lock
        self.conn.commit()
        t.join()
        self.assertEqual(errors, [])
        companies = {r[0] for r in self.conn.execute("SELECT company FROM applications")}
        self.assertEqual(companies, {"A", "B"})


if __name__ == "__main__":
    unittest.main()
