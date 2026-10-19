# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo provides the tools, skills and MCP servers that let Claude Code act as a job application agent. Target capabilities (from README):

- Search for job openings
- Write cover letters
- Track application status
- Update that tracking from the email inbox

## Current state

- `tracking/`: application-tracking store (SQLite, stdlib `sqlite3`). Schema in `tracking/schema.sql`, access in `tracking/db.py`.
- `jobs/`: `scrape.py` (JobSpy per term/location/site, dedupe, temp dir for the evaluator), `add_leads.py` (evaluator output to `lead` rows).
- `inbox/fetch.py`: read-only IMAP fetch of new INBOX mail into a temp dir (stdlib only).
- `tracking/api.py` + `web/`: local web UI (FastAPI + Vite/React/Mantine) to browse applications and review leads. See Tracking UI.
- Skills: `update-tracking`, `check-inbox`, `grill-preferences`, `find-jobs`, `review-leads`. Agents (Haiku, Read-only): `inbox-triage`, `job-evaluator`.
- `tests/`: stdlib `unittest`.
- `data/` (gitignored, personal data): `tracking.db`, `preferences.toml`, `tracking-pre-migration.db` (backup from the status migration), the original tracking sheet, cover letters. Never commit or publish anything from it.

## Tracking DB

- Location: `data/tracking.db`. Create or upgrade it with `uv run python -m tracking.db` (idempotent).
- Write through `tracking.db.connect()`, which turns on foreign keys and the busy timeout. From the shell: `uv run python -m tracking.db sql "<SQL with ?>" [params...]`. Use the `sqlite3` CLI only for reads, e.g. `sqlite3 data/tracking.db "SELECT company, role, status FROM applications"`.
- Status changes are logged to `events` by a trigger. Add your own `email`/`note` event when you know the cause.
- Statuses: `lead` → `to_apply` (user wants to apply) → `applied` → `interview` → `offer`; `rejected` = the company said no; `dismissed` = the user said no; also `withdrawn`, `ghosted`. `init()` migrates older DBs to this status list once, with a backup.
- Notes from `source='evaluator'` are the evaluator's reasons, and from `source='review'` the user's denial reasons. The job evaluator's digest reads them.
- `inbox_state.last_mail_at`: received time of the newest processed mail. The inbox check reads only newer mail.
- Backup: `sqlite3 data/tracking.db ".backup data/tracking-backup.db"`

## Tracking UI

- Build once (and after frontend changes): `pnpm --dir web install && pnpm --dir web build`. Run: `uv run python -m tracking.api`, then open http://127.0.0.1:8765.
- Dev: run the API as above plus `pnpm --dir web dev` (Vite proxies `/api`). Frontend tests: `pnpm --dir web test`.
- Read-only except the lead review. Review decisions stay in the browser (localStorage) until "Write decisions", then `POST /api/review` applies them in one transaction, only to rows still `lead` (others come back as conflicts). Same rules as the review-leads skill (which still works), except that a skip in the UI never carries a reason and never writes.
- Reason checkboxes come from `[review].reasons` in `data/preferences.toml`. Ticked reasons and free text become one `review` note.
- Keep it local: binds `127.0.0.1`, and only `127.0.0.1`/`localhost` Host headers are accepted.

## Inbox

- Setup: copy `.env.example` to `.env` (gitignored) and fill in the goneo IMAP credentials.
- Fetch only: `uv run --env-file .env inbox/fetch.py [--since YYYY-MM-DD]`. Normally run through the check-inbox skill, which triages, updates and advances the stamp.
- Never Read fetched mail bodies in the main session. That is the triage agent's job.

## Job search

- `data/preferences.toml` drives the JobSpy search (`[search]`: terms, locations, max_age_days, sites, exclude_companies) and the evaluator (`[evaluator].want`). Create or refine it with the grill-preferences skill.
- Weekly flow: find-jobs (scrape → job-evaluator → leads), then review-leads (yes → `to_apply`, no → `dismissed`, reason optional).
- Scrape only: `uv run jobs/scrape.py` (prints the temp dir). Never Read the run files in the main session; the job-evaluator agent does that.

## LinkedIn MCP

- `.mcp.json` runs the `linkedin` server ([stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server)) in Docker, pinned by digest. It sees only `~/.linkedin-mcp` (the session, outside the repo). Docker Desktop must be running.
- Tool policy is in `.claude/settings.json`: only the read-only job and company tools are allowed, and everything that acts as the user or reads messages is denied. Keep it that way. LinkedIn's terms forbid automation, so use it sparingly and from one session at a time.
- Log in (once, and again when the session expires): run the command below, open http://127.0.0.1:6080, sign in, then stop it.
  `docker run -it --rm -v ~/.linkedin-mcp:/home/pwuser/.linkedin-mcp -p 127.0.0.1:6080:6080 stickerdaniel/linkedin-mcp-server:4.26.2@sha256:c7aa139cfaaecc8ae9f5e810d6517e5e36b5a1a52cadcb4eef6f0832810b4da6 --login --login-viewer`
- Upgrade: change the tag and digest in `.mcp.json` (and in the login command above), list the new version's tools, and put every tool in either the allow or the deny list.
- Saving a LinkedIn job with posting text: see the update-tracking skill.

## Commands

- Test: `uv run python -m unittest discover tests`
- Add a dependency: `uv add <package>` (dev-only: `uv add --dev <package>`)
