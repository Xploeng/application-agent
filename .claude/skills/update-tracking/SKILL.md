---
name: update-tracking
description: Update the job application tracking DB. Use when the user reports news about an application ("Globex invited me", "Initech rejected me"), wants to add an application, or wants to note something about one. Also the write rules for check-inbox.
---

# Update tracking

The tracking store is `data/tracking.db` (SQLite, personal data, gitignored).

## Read and write

- **Read** with the sqlite3 CLI:
  `sqlite3 -box data/tracking.db "SELECT id, company, role, status, applied_on FROM applications ORDER BY company"`
- **Write** only through the helper, which turns on the store's checks. Run one statement per call, with `?` placeholders and values as arguments:
  `uv run python -m tracking.db sql "UPDATE applications SET status = ? WHERE id = ?" interview 23`

Never write with the sqlite3 CLI.

## Schema (relevant columns)

`applications`:
- `id`
- `company`, `role` (both required)
- `url` (unique)
- `location`, `start_date`, `work_mode`, `focus`, `pay`
- `source` (manual, linkedin, jobspy, excel, ...)
- `status`
- `applied_on` (ISO date)
- `notes`
- `posting_text`, `posting_captured_at`
- `updated_at`

`status` is one of: `lead`, `applied`, `interview`, `offer`, `rejected`, `withdrawn`, `ghosted`.

`events`:
- `application_id`
- `at`: set automatically
- `kind`: `status_change` | `email` | `note` | `import`
- `detail`
- `source`: manual, inbox, ...

A trigger writes a `status_change` event on every status change, so never insert those yourself.

## How to apply a request

1. **Find the application.** Match the company case-insensitively and allow for partial names (`... WHERE company LIKE '%globex%'`).
   - **Exactly one match:** use it.
   - **Several matches:** ask the user which role they mean before writing anything.
   - **No match:** say so and offer to add it. Never create one silently.
2. **Status change:** `UPDATE applications SET status = ? WHERE id = ?`. If the user gives a date for an application they sent, also set `applied_on` when it is empty.
3. **New application:** `INSERT INTO applications (company, role, status, source, ...) VALUES (...)`.
   - `status` defaults to `lead` unless the user says otherwise, and `source` defaults to `manual`.
   - If the user gives posting text or a reachable posting URL, store the text in `posting_text` and set `posting_captured_at = strftime('%Y-%m-%dT%H:%M:%S','now')`.
4. **Note:** `INSERT INTO events (application_id, kind, detail, source) VALUES (?, 'note', ?, 'manual')`. Notes never change the status.
5. **If the helper reports an error** (for example `CHECK constraint failed`), tell the user what failed and why. Don't retry with altered data unless the user asks.
6. **Confirm briefly** what changed: company, role, old status and new status.
