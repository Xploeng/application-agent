-- Tracking store schema. Idempotent: safe to run on every init.

CREATE TABLE IF NOT EXISTS applications (
  id                  INTEGER PRIMARY KEY,
  company             TEXT NOT NULL,
  role                TEXT NOT NULL,
  url                 TEXT UNIQUE,
  location            TEXT,
  start_date          TEXT,
  work_mode           TEXT,
  focus               TEXT,
  pay                 TEXT,
  source              TEXT,
  status              TEXT NOT NULL DEFAULT 'lead' CHECK (status IN
                        ('lead','applied','interview','offer','rejected','withdrawn','ghosted')),
  applied_on          TEXT,
  updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
  notes               TEXT,
  posting_text        TEXT,
  posting_captured_at TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS events (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES applications(id),
  at             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
  kind           TEXT NOT NULL CHECK (kind IN ('status_change','email','note','import')),
  detail         TEXT,
  source         TEXT
) STRICT;

CREATE INDEX IF NOT EXISTS events_application ON events(application_id);

-- Every status change is logged here, whoever writes it; source is unknown at this level.
CREATE TRIGGER IF NOT EXISTS applications_status_change
AFTER UPDATE OF status ON applications
WHEN OLD.status IS NOT NEW.status
BEGIN
  INSERT INTO events (application_id, kind, detail)
  VALUES (NEW.id, 'status_change', OLD.status || ' -> ' || NEW.status);
  UPDATE applications SET updated_at = strftime('%Y-%m-%dT%H:%M:%S','now') WHERE id = NEW.id;
END;

-- Inbox check: received time (UTC) of the newest processed mail. Seeded with the
-- install time, since tracking is up to date then; later inits leave it alone.
CREATE TABLE IF NOT EXISTS inbox_state (
  id           INTEGER PRIMARY KEY CHECK (id = 1),
  last_mail_at TEXT NOT NULL
) STRICT;

INSERT OR IGNORE INTO inbox_state VALUES (1, strftime('%Y-%m-%dT%H:%M:%S+00:00','now'));
