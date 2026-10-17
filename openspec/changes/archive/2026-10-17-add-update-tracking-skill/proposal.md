## Why

The tracking DB exists, but updating it still means writing SQL by hand. Most status changes (confirmations, interview invites, rejections) arrive by email, buried in an inbox that is mostly unrelated mail. Claude should be able to apply updates on request and pick them up from the inbox, without spending many tokens on noise.

## What Changes

- Add an `update-tracking` skill for manual updates in a session ("Globex invited me", "add Hooli, ML Engineer"). It knows the schema and allowed statuses, and writes through `tracking.db.connect()`.
- Add a `check-inbox` skill, started manually in a session, that:
  - runs a read-only fetch script for mails newer than the last processed one,
  - hands them to a small triage subagent that discards the noise,
  - applies the relevant results to existing applications using the `update-tracking` rules, with no confirmation step (confirmations of receipt set `applied` and fill in the application date),
  - reports what changed and what could not be matched.
- Add an `inbox/fetch.py` script, stdlib only, that reads the goneo IMAP inbox without changing it:
  - nothing is marked read,
  - only the text/html or text/plain body part is fetched, never images or attachments,
  - output goes to a temporary directory that is deleted after the run.
- Add an `inbox-triage` subagent (Haiku, `Read` tool only). It discards mails on subject and sender first, and opens a body only when the header isn't enough. It returns only relevant mails, each with its date.
- Store the date of the newest processed mail in the tracking DB, so each run reads only newer mail. Nothing else about individual mails is stored.
- Credentials (`IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD`) live in a gitignored `.env`.

Non-goals:

- Creating new applications from the inbox. Unmatched relevant mails are only reported.
- Scheduled or unattended runs.
- Folders other than INBOX.
- Airtight robustness: the user reads their mail anyway.

This change also absorbs the former `add-inbox-check` change.

## Capabilities

### New Capabilities

- `tracking-updates`: Manual, in-session updates to the tracking store: changing status, adding applications, adding notes and events.
- `inbox-check`: Read-only inbox fetch, token-light triage of new mail, and automatic status updates for existing applications.

### Modified Capabilities

<!-- none: application-tracking requirements are unchanged; the last-mail stamp is inbox-check state -->

## Impact

- New files:
  - `.claude/skills/update-tracking/SKILL.md`
  - `.claude/skills/check-inbox/SKILL.md`
  - `.claude/agents/inbox-triage.md`
  - `inbox/fetch.py`
  - a test for the fetch script's parsing
- `tracking/schema.sql`: one small table for the last-mail stamp (additive, `IF NOT EXISTS`).
- No new dependencies: `imaplib`, `email` and `html.parser` from the stdlib, and `.env` is loaded via `uv run --env-file`.
- The user creates `.env` with the goneo IMAP credentials.
