import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tracking.db import SCHEMA, connect, init, run_sql

NEW_STATUSES = "('lead','to_apply','applied','interview','offer','rejected','withdrawn','ghosted','dismissed'))"
OLD_STATUSES = "('lead','applied','interview','offer','rejected','withdrawn','ghosted'))"


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

    def test_inbox_stamp_seeded_once(self):
        with self.conn:
            self.conn.execute("UPDATE inbox_state SET last_mail_at = '2026-01-01T00:00:00+00:00'")
        init(self.path)
        self.assertEqual(
            self.conn.execute("SELECT last_mail_at FROM inbox_state").fetchall(), [("2026-01-01T00:00:00+00:00",)]
        )

    def test_run_sql_commits_and_validates(self):
        app = self.add(status="applied")
        run_sql("UPDATE applications SET status = ? WHERE id = ?", ["interview", str(app)], self.path)
        self.assertEqual(self.events(app), [("applied -> interview",)])
        self.assertEqual(run_sql("SELECT status FROM applications WHERE id = ?", [str(app)], self.path), [("interview",)])
        with self.assertRaises(sqlite3.IntegrityError):
            run_sql("UPDATE applications SET status = ? WHERE id = ?", ["rejectd", str(app)], self.path)

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


class StatusMigrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "tracking.db"
        old_schema = SCHEMA.read_text()
        self.assertIn(NEW_STATUSES, old_schema)
        conn = sqlite3.connect(self.path)
        conn.executescript(old_schema.replace(NEW_STATUSES, OLD_STATUSES))
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            conn.execute("INSERT INTO applications (id, company, role, status) VALUES (7, 'Acme', 'Eng', 'applied')")
            conn.execute("INSERT INTO applications (id, company, role, url) VALUES (9, 'Beta', 'ML', 'https://x/1')")
            conn.execute("UPDATE applications SET status = 'rejected' WHERE id = 7")  # trigger writes an event
            conn.execute("INSERT INTO events (application_id, kind, detail) VALUES (9, 'note', 'hi')")
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_old_schema_migrates_and_keeps_data(self):
        init(self.path)
        conn = connect(self.path)
        try:
            self.assertEqual(conn.execute("SELECT id, company, status FROM applications ORDER BY id").fetchall(),
                             [(7, "Acme", "rejected"), (9, "Beta", "lead")])
            self.assertEqual(conn.execute("SELECT application_id, kind, detail FROM events ORDER BY id").fetchall(),
                             [(7, "status_change", "applied -> rejected"), (9, "note", "hi")])
            with conn:
                conn.execute("UPDATE applications SET status = 'to_apply' WHERE id = 9")
                conn.execute("UPDATE applications SET status = 'dismissed' WHERE id = 7")
            self.assertEqual(conn.execute("SELECT count(*) FROM events WHERE kind = 'status_change'").fetchone()[0], 3)
            with self.assertRaises(sqlite3.IntegrityError), conn:
                conn.execute("UPDATE applications SET status = 'rejectd' WHERE id = 9")
            with self.assertRaises(sqlite3.IntegrityError), conn:  # FK to applications still enforced
                conn.execute("INSERT INTO events (application_id, kind) VALUES (999, 'note')")
            with self.assertRaises(sqlite3.IntegrityError), conn:  # UNIQUE url survived the rebuild
                conn.execute("INSERT INTO applications (company, role, url) VALUES ('C', 'R', 'https://x/1')")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            conn.close()
        self.assertTrue((Path(self.tmp.name) / "tracking-pre-migration.db").exists())

    def test_second_init_is_a_no_op(self):
        init(self.path)
        backup = Path(self.tmp.name) / "tracking-pre-migration.db"
        backup.unlink()
        init(self.path)
        self.assertFalse(backup.exists())


if __name__ == "__main__":
    unittest.main()
