## 1. Store additions

- [x] 1.1 Add the `inbox_state` table plus its `INSERT OR IGNORE` seed (now) to `tracking/schema.sql` and run `uv run python -m tracking.db` against the existing DB; verify `last_mail_at` is about the current time, a second init leaves it unchanged, and the 28 applications are untouched
- [x] 1.2 Add the `sql` subcommand to `tracking/db.py` (one statement, positional params, one transaction, prints rows); verify with a unittest that a parameterised UPDATE commits and an invalid status is rejected, and that `uv run python -m unittest discover tests` passes

## 2. Update-tracking skill

- [x] 2.1 Write `.claude/skills/update-tracking/SKILL.md` (schema summary, statuses, read via sqlite3 / write via `tracking.db sql`, ambiguity → ask, notes as `note`/`manual` events); verify by asking in a session to add a note to one application and checking the event row exists and status is unchanged

## 3. Inbox fetch script

- [x] 3.1 Write `inbox/fetch.py` BODYSTRUCTURE parsing, part selection (html > plain, skip attachments) and HTML-to-text; verify with `tests/test_fetch.py` covering single-part, multipart/alternative and mixed-with-PDF structures and an HTML sample with `<img>`/`<script>`, passing offline
- [x] 3.2 Add the IMAP side: `.env` check, `EXAMINE INBOX`, `SINCE` search from the stored stamp or `--since`, strict `INTERNALDATE` filter, `BODY.PEEK` fetches, temp-dir output, printed summary; verify the script refuses to run with a missing `.env` value and names it
- [x] 3.3 Add `.env.example`; verify `git check-ignore .env` matches and `.env.example` is not ignored

## 4. Triage agent and check-inbox skill

- [x] 4.1 Write `.claude/agents/inbox-triage.md` (`model: haiku`, `tools: Read`, header-first instructions, output schema); verify it appears in the agent list of a new session
- [x] 4.2 Write `.claude/skills/check-inbox/SKILL.md` (flow, kind→status mapping, confirmation fills empty `applied_on`, oldest-first apply, never insert, stamp after success, temp-dir cleanup, report); verify the skill is listed in a new session

## 5. End-to-end check (needs the user's `.env`)

- [x] 5.1 Run `/check-inbox` on the real inbox with `--since` a few days back; verify a mail that was unread before is still unread, the temp dir is gone, `inbox_state.last_mail_at` equals the newest fetched mail, and the report lists fetched/discarded/applied/unmatched counts
- [x] 5.2 Run `/check-inbox` again immediately; verify it fetches 0 mails (or only mail that arrived since)

## 6. Documentation

- [x] 6.1 Update CLAUDE.md: the two skills, `.env` setup, `tracking.db sql` helper, `inbox/` script; verify listed commands run as written
