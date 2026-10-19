# Job application agent

Tools, skills and MCP servers that turn [Claude Code](https://claude.com/claude-code) into a job application assistant. It finds openings, helps you decide which to pursue, writes cover letters in your own style, and keeps a tracking database up to date from your email inbox.

Everything runs locally. Your personal data (applications, CV, letters, preferences) lives in `data/`, which is gitignored.

## What it does

| Area | How you use it | What happens |
|---|---|---|
| **Preferences** | `/grill-preferences` | Claude interviews you about roles, locations, seniority and deal-breakers, and writes `data/preferences.toml`. |
| **Job search** | `/find-jobs` | Scrapes Indeed, LinkedIn (guest search), Glassdoor and Google Jobs via [JobSpy](https://github.com/speedyapply/JobSpy). A Haiku subagent drops clear mismatches. The rest become `lead`s with the full posting text and a one-line reason. Dismissed jobs never come back, and your past decisions guide later runs. |
| **Lead review** | Tracking UI (below), or `/review-leads` | Go through leads one at a time: apply (`to_apply`), dismiss (with optional reasons), or skip for later. |
| **Profile** | `/build-profile` | Builds `data/profile.md`, your facts for applications, from your CV and documents, your LinkedIn profile and your sample letters, then asks about the gaps. |
| **Cover letters** | `/write-cover-letter <company or id>` | Writes a letter for one tracked posting, in the posting's language and your style, using only facts from your profile. Saved to `data/generated_letters/`. |
| **Tracking** | Just tell Claude: "I applied to Globex", "Initech rejected me" | The update-tracking skill writes it to the SQLite tracking DB, with a full status history. |
| **Inbox** | `/check-inbox` | Fetches new mail over IMAP (read-only). A Haiku subagent picks out application mails (confirmations, invites, rejections, offers), and Claude updates the matching applications. |
| **LinkedIn** (optional) | Ask Claude about a LinkedIn job or company | A read-only LinkedIn MCP server for job details, company profiles and saved jobs. Everything that would act as you is blocked. |

### Tracking UI

A local web app for browsing the tracking DB and reviewing leads without Claude:

- **Table:** all applications with a colour-coded status, role, company and link. Status chips filter the list.
- **Detail view:** the stored posting, rendered as formatted text.
- **Review:** one lead at a time, with keyboard shortcuts:
  - `Y` apply, `N` dismiss, `S` skip, `U` undo.
  - Optional reason checkboxes, from `[review].reasons` in your preferences, plus free text.
  - Decisions stay in the browser until you press **Write decisions**. They are then saved in one transaction.
  - A lead that changed in the meantime (for example through the inbox check) is reported, not overwritten.

### Application statuses

```
lead --> to_apply --> applied --> interview --> offer
  |                      |
  v                      +--> rejected (company said no) / ghosted / withdrawn
dismissed (you said no)
```

## Setup after cloning

### Prerequisites

- [Claude Code](https://claude.com/claude-code)
- [uv](https://docs.astral.sh/uv/). It installs Python 3.12 and the dependencies for you.
- [Node.js](https://nodejs.org/) and [pnpm](https://pnpm.io/), for the tracking UI.
- Optional: an email account with IMAP access, for `/check-inbox`.
- Optional: [Docker Desktop](https://www.docker.com/products/docker-desktop/), for the LinkedIn MCP server.

### 1. Install and create the database

```sh
uv sync                                # Python dependencies
uv run python -m tracking.db           # creates data/tracking.db (safe to re-run)
pnpm --dir web install                 # UI dependencies
pnpm --dir web build                   # builds the UI into web/dist
```

### 2. Email inbox (optional)

```sh
cp .env.example .env
```

Fill in `IMAP_HOST`, `IMAP_USER` and `IMAP_PASSWORD` (IMAP over SSL, port 993). `.env` is gitignored. The inbox check reads only mail received after the database was created. To pick up older mail once, run:

```sh
uv run --env-file .env inbox/fetch.py --since YYYY-MM-DD
```

### 3. LinkedIn (optional)

Docker Desktop must be running. Log in once (and again whenever the session expires):

```sh
docker run -it --rm -v ~/.linkedin-mcp:/home/pwuser/.linkedin-mcp -p 127.0.0.1:6080:6080 \
  stickerdaniel/linkedin-mcp-server:4.26.2@sha256:c7aa139cfaaecc8ae9f5e810d6517e5e36b5a1a52cadcb4eef6f0832810b4da6 \
  --login --login-viewer
```

Open http://127.0.0.1:6080, sign in, then stop the container. The session is stored in `~/.linkedin-mcp`, outside the repo. Claude Code starts the server from `.mcp.json` and asks you to approve it on first use. LinkedIn's terms forbid automation, so use it sparingly.

### 4. Your data

Start Claude Code in the repo (`claude`), then:

1. Run `/grill-preferences` to create `data/preferences.toml`. Optionally add reason checkboxes for the review page by hand:
   ```toml
   [review]
   reasons = ["too senior", "consulting", "boring use case"]
   ```
2. Put your CV, transcripts and similar documents into `data/about_me/`.
3. Put cover letters you have written before into `data/Cover_letters/`, as PDF or `.txt`. They are the style reference.
4. Run `/build-profile` to create `data/profile.md`.

If you are coming from a spreadsheet, ask Claude to import it. The import was a guided one-off migration (see `openspec/specs/excel-import/`).

## Everyday use

```
/find-jobs                          weekly: new leads with posting text
uv run python -m tracking.api       then review at http://127.0.0.1:8765
/write-cover-letter Hooli         for a lead you marked "apply"
"I applied to Hooli"              Claude updates the tracking DB
/check-inbox                        confirmations, invites, rejections
```

The UI server runs until you stop it (Ctrl+C) and can stay open while Claude works. It writes to the database only when you press **Write decisions**.

## Project layout

```
tracking/      SQLite store: schema.sql, db.py (connect, init, migrations, `sql` helper), api.py (UI backend)
jobs/          scrape.py (JobSpy search, dedupe), add_leads.py (evaluator output -> leads)
inbox/         fetch.py (read-only IMAP fetch, stdlib only)
web/           tracking UI: Vite + React + TypeScript + Mantine
.claude/       skills, subagents (inbox-triage, job-evaluator), LinkedIn tool policy
openspec/      specs per capability and the archived change history
tests/         Python unittest suite
data/          your personal data (gitignored, never commit it)
```

## Development

```sh
uv run python -m unittest discover tests   # Python tests
pnpm --dir web test                        # frontend tests
pnpm --dir web dev                         # UI with hot reload (run the API alongside it)
```

- Changes are planned with [OpenSpec](https://github.com/Fission-AI/OpenSpec): `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`. The current behaviour of each capability is described in `openspec/specs/`.
- `CLAUDE.md` holds the working rules Claude follows in this repo.
- Keep the LinkedIn tool policy in `.claude/settings.json` read-only.
