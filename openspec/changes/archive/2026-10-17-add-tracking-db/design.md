## Context

The repo is a fresh `uv` project (Python >=3.12, no dependencies, no package layout). The local SQLite library is 3.49, so `STRICT` tables, `CHECK` constraints and triggers are all available. Everything runs on one laptop. Writers are the user via Claude, and later the job scraper and the inbox check, which may run while Claude is working. See proposal.md for motivation and specs/ for the behaviour contract.

## Goals / Non-Goals

**Goals:**

- Put every invariant (required fields, allowed statuses, unique URL, status history) in the database itself, so every writer is held to the same rules, including LLM-driven ones and ad-hoc SQL.
- Keep the code footprint tiny: one schema file, one small Python module.

**Non-Goals:**

- No ORM, no migration framework, no CRUD layer. Later changes add whatever access helpers they need.
- No permanent import code. The Excel migration runs once, interactively.

## Decisions

### SQLite through the stdlib `sqlite3` module

Alternatives considered:

- DuckDB: allows only one read-write process at a time, which conflicts with concurrent writers, and adds a ~30MB dependency.
- Excel as the store: Excel locks the file while it's open and offers no validation.
- JSON/CSV: last write wins, no constraints.
- Postgres: needs a server.

SQLite needs no dependencies and is a single file. Claude can also inspect it with the `sqlite3` CLI that ships with macOS.

### Layout

```
tracking/
  schema.sql      -- tables, constraints, triggers; all CREATE ... IF NOT EXISTS
  db.py           -- DB_PATH, connect(path=DB_PATH), init(path=DB_PATH)
data/
  tracking.db     -- gitignored
```

- `init()` executes `schema.sql`. Because every statement uses `IF NOT EXISTS`, running it again is a no-op.
- `connect()` is the one sanctioned way to open the store. It sets the per-connection pragmas (`foreign_keys = ON`, `busy_timeout = 5000`) and returns a plain `sqlite3.Connection`.
- `journal_mode = WAL` is set once in `init()`. It is persistent in the file and lets readers and a writer work concurrently. The busy timeout makes a second writer wait instead of failing.
- `.gitignore` ignores the whole `data/` folder. It holds the database and its `-wal`/`-shm`/`-journal` side files, plus the source sheet and cover letters, all personal data.

### Schema

```sql
CREATE TABLE IF NOT EXISTS applications (
  id                  INTEGER PRIMARY KEY,
  company             TEXT NOT NULL,
  role                TEXT NOT NULL,
  url                 TEXT UNIQUE,              -- NULLs don't collide
  location            TEXT,
  start_date          TEXT,                     -- ISO date (or year) the job would start
  work_mode           TEXT,                     -- Flexible, Hybrid, On-site, Remote
  focus               TEXT,                     -- e.g. Agentic, RL, Generative
  pay                 TEXT,                     -- free text: '60', '70-90k', 'TV-Öd E13'
  source              TEXT,                     -- linkedin, jobspy, referral, excel, ...
  status              TEXT NOT NULL DEFAULT 'lead' CHECK (status IN
                        ('lead','applied','interview','offer','rejected','withdrawn','ghosted')),
  applied_on          TEXT,                     -- ISO date
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
  source         TEXT                           -- manual, inbox, excel-import, ...; NULL if unknown
) STRICT;
```

- `start_date`, `work_mode`, `focus` and `pay` came from the Excel sheet's columns. They are free text because the sheet's values are too irregular to constrain (pay ranges, tariff names).
- `source` is free text rather than a `CHECK` list. New tools add new sources, and constraining the field gains nothing.
- Timestamps are stored as UTC ISO text, the format SQLite's own date functions produce.

### Status history via trigger

An `AFTER UPDATE OF status ON applications WHEN OLD.status IS NOT NEW.status` trigger inserts a `status_change` event with `detail = 'old -> new'` and refreshes `updated_at`.

Alternative considered: each tool writes its own event. That fails silently as soon as one writer forgets, for example Claude running ad-hoc SQL. The trigger can't know *why* the status changed, so its event has `source = NULL`. Tools that know the cause (the inbox check, say) add their own `email` or `note` event next to it.

Append-only is a convention, not enforced. A `BEFORE DELETE` trigger would also block legitimate cleanup.

### Excel import: Claude-guided, ephemeral

The import is a one-off apply-phase task, not shipped code and not a skill:

```
data/Application-Tracking.ods --(soffice --headless --convert-to xlsx, into scratch dir)--> tmp.xlsx
 tmp.xlsx --(openpyxl, read-only)--> import_staging (all TEXT, original headers)
                                                           |
                               Claude proposes column + status mapping, shows samples,
                               asks about ambiguous dates / unknown statuses
                                                           |
                                                   user approves
                                                           v
                     BEGIN; INSERT applications ...; INSERT events (kind='import',
                     source='excel-import') ...; COMMIT          -- any failure: ROLLBACK
                                                           |
                                    user confirms result --> DROP TABLE import_staging
```

- The sheet is `.ods`, which openpyxl can't read. LibreOffice (installed) converts it to a temporary `.xlsx` outside the repo, and the original is never touched. `openpyxl` is a dev dependency (`uv add --dev openpyxl`), not a runtime one. Real spreadsheet dates arrive as `datetime` values, and text dates are left for Claude to interpret.
- Screenshot-reference columns are left out of the mapping, and `posting_text` stays NULL.
- The import inserts rows with their mapped status directly, so the status trigger does not fire. The `import` event records the original sheet status in `detail` for traceability.

## Risks / Trade-offs

- [Writer opens the DB without `connect()` (e.g. raw `sqlite3` CLI), so foreign keys are off] → Constraints that matter most (`NOT NULL`, `CHECK`, `UNIQUE`, the status trigger) don't depend on the pragma. CLAUDE.md tells Claude to write through `connect()` and to use the CLI read-only.
- [Single file on one laptop: disk loss means data loss] → A backup is copying one file, ideally via `sqlite3 data/tracking.db ".backup ..."` so the copy is consistent under WAL. Automated backups are left for later.
- [`STRICT` rejects wrongly typed values, e.g. an integer year in a TEXT column] → This is intended. Import values are text anyway.
- [Mapping errors in the one-time import] → Staging keeps the raw data until the user confirms, and the Excel file is never modified, so the import can be redone from scratch.

## Migration Plan

1. Add schema, module and `.gitignore` entries, then run `init()`.
2. Run the Claude-guided import once the user provides the sheet.
3. After the user confirms the result, drop staging. The Excel file stays as the user's archive.

Rollback: delete `data/tracking.db` and re-run `init()`. Nothing else depends on it yet.
