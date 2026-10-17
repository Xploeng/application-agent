## 1. Store setup

- [x] 1.1 Add `data/` to `.gitignore`; verify `git status` no longer lists `data/` and `git check-ignore data/tracking.db-wal` matches
- [x] 1.2 Write `tracking/schema.sql` (both `STRICT` tables, `CHECK` constraints, status-change trigger, all `IF NOT EXISTS`) as in design.md; verify `sqlite3 :memory: < tracking/schema.sql` runs twice in a row without error
- [x] 1.3 Write `tracking/db.py` with `DB_PATH`, `connect()` (sets `foreign_keys` and `busy_timeout`) and `init()` (runs the schema, sets WAL, creates `data/`); verify `uv run python -c "from tracking.db import init; init()"` creates `data/tracking.db` in WAL mode

## 2. Behaviour checks

- [x] 2.1 Add `tests/test_tracking_db.py` (stdlib `unittest`, temp DB file) covering the application-tracking scenarios: re-init keeps rows, missing company/role rejected, duplicate URL rejected, NULL URLs allowed, invalid status rejected, status change writes exactly one `status_change` event, same-value update writes none, event for unknown application rejected, two connections writing concurrently both commit; verify `uv run python -m unittest discover tests` passes

## 3. Documentation

- [x] 3.1 Update CLAUDE.md with the DB location, "write through `tracking.db.connect()`, use the `sqlite3` CLI read-only", the backup command, and the test command; verify the commands listed there run as written

## 4. Excel import (one-time, interactive, needs the user's sheet)

- [x] 4.0 Add `openpyxl` as a dev dependency (`uv add --dev openpyxl`); verify `uv run python -c "import openpyxl"` succeeds
- [x] 4.1 Convert `data/Application-Tracking.ods` to a temporary `.xlsx` with LibreOffice headless (outside the repo), then read it with openpyxl into an `import_staging` table (all TEXT, original headers); verify the staged row count equals the sheet's data rows and `applications` is still empty
- [x] 4.2 Propose the column and status mapping to the user with sample rows, leaving out screenshot-reference columns and listing ambiguous dates and unknown statuses as questions; verify the user has explicitly approved the final mapping
- [x] 4.3 Insert approved rows into `applications` plus one `kind='import'`, `source='excel-import'` event each, in a single transaction (rollback on any error); verify application count equals approved rows, every application has an import event, `posting_text` is NULL for all, and the Excel file's checksum is unchanged
- [x] 4.4 Show the user a summary (counts per status, a few sample rows) and, after they confirm, `DROP TABLE import_staging`; verify the table no longer exists
