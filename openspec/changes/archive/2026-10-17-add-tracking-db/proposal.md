## Why

Job applications are tracked by hand in an Excel sheet, which the agent cannot safely read or write: Excel locks the file while open and offers no validation. The other planned changes (job scraper, update-tracking skill, inbox check) all need one shared, writable store, so it has to exist first.

## What Changes

- Add a local SQLite database (one file, Python stdlib `sqlite3`, no new dependencies) holding applications and their status history.
- Two tables: `applications` (one row per job, current status, URL, full posting text) and `events` (append-only history of status changes, emails and notes).
- Store the full posting text in the database, because postings disappear from job sites after a while.
- Enforce allowed status values and required fields in the schema, so writes from LLM-driven tools cannot store invalid data.
- Keep the whole `data/` folder (database, source sheet, cover letters) gitignored, since it holds personal data.
- Migrate the existing Excel sheet once, with Claude doing the mapping: raw rows go into a staging table, Claude proposes a column and status mapping, the user approves it, and only then are rows inserted. Screenshot references in the sheet are ignored, and `posting_text` stays empty for imported rows.

Non-goals: a GUI for browsing the data (separate change), ongoing sync with Excel, and cloud or multi-machine access. Everything runs on one laptop.

## Capabilities

### New Capabilities

- `application-tracking`: The tracking store: what an application and an event are, the allowed statuses, posting capture, and how tools read and write records.
- `excel-import`: One-time, user-approved migration of the existing Excel tracking sheet into the tracking store.

### Modified Capabilities
<!-- none: no existing specs -->

## Impact

- New files: schema definition and DB initialisation, plus import instructions for Claude.
- `.gitignore`: ignore the whole `data/` folder.
- No new runtime dependencies. `openpyxl` is added as a dev dependency for the one-time import.
- Later changes (`add-job-scraper`, `add-update-tracking-skill`, `add-inbox-check`) build on this schema.
