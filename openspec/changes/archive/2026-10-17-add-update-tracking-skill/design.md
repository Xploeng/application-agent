## Context

The tracking store from `application-tracking` exists: `tracking/schema.sql`, plus `tracking/db.py` with `connect()` and `init()`. CLAUDE.md says to write only through `connect()` and to use the `sqlite3` CLI read-only. The mail is on a goneo mail server with IMAP. Everything runs manually in a Claude Code session on one laptop. See proposal.md for motivation and specs/ for behaviour.

## Goals / Non-Goals

**Goals:**

- Keep the token cost of triage close to "one header line per unrelated mail".
- Use stdlib only, with as little code as possible. Claude does the matching and judgment, and the scripts only do I/O.

**Non-Goals:**

- No batching or parallel triage agents. A single triage agent handles a run.
- No retry or recovery logic. Being robust enough is enough, because the user reads their mail.

## Decisions

### Flow

```
/check-inbox (main Claude)
  1. uv run --env-file .env inbox/fetch.py [--since YYYY-MM-DD]
       -> prints: temp dir path, mail count, newest INTERNALDATE
       -> <tmp>/headers.json  [{uid, date, from, subject}]
          <tmp>/<uid>.txt     body text (<= 4000 chars)
  2. Agent(inbox-triage, prompt = "<tmp>")        main Claude never opens the files
       -> JSON array of relevant mails only
  3. main Claude: sqlite3 read to match company/role, then per mail (oldest first)
       UPDATE status (+ applied_on = mail date if NULL, for confirmations)
       + INSERT event(kind='email', source='inbox') via tracking.db sql
  4. set last_mail_at = newest date from step 1; rm -r <tmp>; print report
```

If 0 mails are fetched, steps 2 and 3 are skipped. The stamp is written only in step 4, so a run that dies earlier is simply repeated next time.

### Write helper: `python -m tracking.db sql "<SQL>" [params...]`

Both skills need to write through `connect()` from Bash. Rather than having Claude improvise `python -c` one-liners with nested quoting, `tracking/db.py`'s `__main__` gets one subcommand. It executes a single statement with positional `?` parameters in one transaction and prints any returned rows. Running it with no subcommand still runs `init()`.

Alternative considered: a CRUD CLI (`set-status`, `add`, `note`). It is more code, and Claude would still need raw SQL for anything not covered.

### Last-mail stamp

```sql
CREATE TABLE IF NOT EXISTS inbox_state (
  id           INTEGER PRIMARY KEY CHECK (id = 1),   -- single row
  last_mail_at TEXT NOT NULL                         -- UTC ISO, server receive time
) STRICT;
```

- The timestamp is the server's `INTERNALDATE`, normalised to UTC, not the mail's `Date:` header, which senders control.
- IMAP `SEARCH SINCE` only works by whole day. `fetch.py` searches `UID SEARCH SINCE <stamp date - 1 day>` (the extra day absorbs server time-zone offsets), then keeps only mails whose `INTERNALDATE` is strictly after the stamp.
- The stamp is seeded by `INSERT OR IGNORE INTO inbox_state VALUES (1, <now>)` in `schema.sql`, so the first `init()` after this change sets it to "now". Tracking is up to date at that point, and later inits leave it alone. Because a stamp always exists, there is no lookback default. `--since` overrides the stamp for a single run.

Alternative considered: storing the last UID instead. It is more precise, but UIDs reset when the mailbox's `UIDVALIDITY` changes, and the user asked for a date.

### Read-only fetch in `inbox/fetch.py` (stdlib `imaplib`, `email`, `html.parser`)

1. `IMAP4_SSL(IMAP_HOST, 993)`, then `login`, then **`EXAMINE INBOX`**. The read-only select makes the server refuse any flag change during the session.
2. `UID FETCH <uids> (INTERNALDATE BODYSTRUCTURE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])`. Using `PEEK` means `\Seen` is never set.
3. Walk the BODYSTRUCTURE to find the part number of the first `text/html` part, otherwise the first `text/plain` part, skipping parts with `Content-Disposition: attachment`. A small recursive parser handles the parenthesised BODYSTRUCTURE format.
4. `UID FETCH <uid> (BODY.PEEK[<part>.MIME] BODY.PEEK[<part>])`. Joining the part's MIME header and body and passing them to `email.message_from_bytes` lets the stdlib handle base64, quoted-printable and the character set.
5. HTML is converted to text with an `html.parser.HTMLParser` subclass that collects text and drops `script`, `style` and `img`. Nothing is rendered or requested over the network.
6. The output goes to `tempfile.mkdtemp(prefix="inbox-")`, outside the repo. Bodies are capped at 4000 characters.

If BODYSTRUCTURE parsing fails for a mail, its body file is left empty and the triage decides from the headers. The script never falls back to fetching the whole message, because that would download attachments.

### Triage subagent: `.claude/agents/inbox-triage.md`

- Frontmatter: `model: haiku`, `tools: Read`.
- Instructions: read `headers.json` first and discard on sender and subject. `Read` `<uid>.txt` only for undecided mails. Output a JSON array of `{date, company, role, kind, summary}` for relevant mails only, where kind is one of `confirmation | interview | rejection | offer`. Return `[]` when nothing is relevant.
- With `Read` as its only tool, a hostile mail could at most make it read another local file into the user's own session. The user accepts this ("does not need to be airtight").

Alternative considered: a subagent with no tools. Main Claude would then have to load the raw text to pass it in, which costs more tokens and removes the separation.

### Skills

- `.claude/skills/update-tracking/SKILL.md` covers:
  - a schema summary and the allowed statuses,
  - "read with `sqlite3 data/tracking.db`, write with `uv run python -m tracking.db sql`",
  - asking when a match is ambiguous,
  - `note` events with source `manual`.
- `.claude/skills/check-inbox/SKILL.md` covers the flow above, the kind-to-status mapping, the "never insert, report unmatched" rule, and the report format. For matching and writing it refers to `update-tracking` rather than repeating those rules.
- A committed `.env.example` lists `IMAP_HOST=imap.goneo.de`, `IMAP_USER=` and `IMAP_PASSWORD=` (goneo's documented host, not verified).

## Risks / Trade-offs

- [Haiku misclassifies a mail: a missed rejection, or a false interview] → The user reads their mail anyway. Every inbox write leaves an `email` event, and every run prints its changes, so mistakes are visible and easy to undo with `update-tracking`.
- [BODYSTRUCTURE variants trip the parser] → That mail gets triaged on its headers only. Parser tests cover common shapes: single part, multipart/alternative, mixed with an attachment.
- [A long gap between runs means a big `headers.json`] → Runs are about weekly, and roughly 30 tokens per header line keeps even 1,000 mails at about 30k tokens, fine for one Haiku agent. If that ever hurts, it can be split into batches.
- [Prompt injection via mail content] → The triage agent is read-only, and main Claude only sees its structured output. This is accepted as good enough.
- [Mail arriving during a run] → The stamp is set to the newest mail *fetched*, not to the current time, so such mail is picked up next run.
