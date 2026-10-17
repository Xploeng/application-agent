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
- `inbox/fetch.py`: read-only IMAP fetch of new INBOX mail into a temp dir (stdlib only).
- `.claude/skills/update-tracking`, `.claude/skills/check-inbox`, `.claude/agents/inbox-triage.md` (Haiku, Read-only): the tracking skills.
- `tests/`: stdlib `unittest`.
- `data/` (gitignored, personal data): `tracking.db`, the original tracking sheet, cover letters. Never commit or publish anything from it.

## Tracking DB

- Location: `data/tracking.db`. Create or upgrade it with `uv run python -m tracking.db` (idempotent).
- Write through `tracking.db.connect()`, which turns on foreign keys and the busy timeout. From the shell: `uv run python -m tracking.db sql "<SQL with ?>" [params...]`. Use the `sqlite3` CLI only for reads, e.g. `sqlite3 data/tracking.db "SELECT company, role, status FROM applications"`.
- Status changes are logged to `events` by a trigger. Add your own `email`/`note` event when you know the cause.
- `inbox_state.last_mail_at`: received time of the newest processed mail. The inbox check reads only newer mail.
- Backup: `sqlite3 data/tracking.db ".backup data/tracking-backup.db"`

## Inbox

- Setup: copy `.env.example` to `.env` (gitignored) and fill in the goneo IMAP credentials.
- Fetch only: `uv run --env-file .env inbox/fetch.py [--since YYYY-MM-DD]`. Normally run through the check-inbox skill, which triages, updates and advances the stamp.
- Never Read fetched mail bodies in the main session. That is the triage agent's job.

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
