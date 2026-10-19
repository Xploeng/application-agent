## Why

Finding openings is the main job of this agent, and it is still manual. The user wants a weekly run that pulls postings matching their preferences from many platforms, including niche ones with less competition, and softly pre-filters them. The results land as leads with the posting text stored, to review and accept or deny.

## What Changes

- **New statuses** `to_apply` ("application outstanding") and `dismissed` ("denied", by the user):
  - `rejected` keeps meaning the company said no.
  - Because SQLite cannot alter a `CHECK` constraint, this needs a one-off rebuild of the `applications` table, done in one transaction after a backup. The `update-tracking` skill learns the two statuses.
- **Preferences file** `data/preferences.toml` (gitignored) with two parts:
  - a structured **Search** section: terms, locations and radius, age window, JobSpy sites,
  - free-text **What I want** for the evaluator.
- **`grill-preferences` skill:** interviews the user one question at a time, starting from patterns in the tracking DB, and writes the preferences file after showing it.
- **Scraper** `jobs/scrape.py`, a thin wrapper around JobSpy `scrape_jobs`. It covers only the sites JobSpy supports, by default those covering Germany: Indeed, LinkedIn guest search (not the LinkedIn MCP), Glassdoor, and Google Jobs, which aggregates niche boards.
  - At most 50 postings per search term per site.
  - Before any LLM sees the postings, the script drops ones that are too old, already in the DB (including dismissed), or duplicated across sites.
- **`job-evaluator` subagent** (Haiku, Read only): a soft filter that drops only clear mismatches. It looks at the title first and reads the description only when needed. It is guided by the preferences and by a digest of past liked and passed-on jobs, generated from the DB at each run.
- **`find-jobs` skill:** scrape, evaluate, then insert the kept jobs as `lead` with URL, posting text and the evaluator's reason.
- **`review-leads` skill:** shows leads as a numbered list and takes answers like "yes 1 3, no 2 consulting". Yes sets `to_apply`, no sets `dismissed`, and reasons are optional.

Non-goals:

- Using the LinkedIn MCP for scraping.
- Job sources beyond what JobSpy supports: no custom scrapers or APIs.
- Scheduled runs.
- A GUI.
- Evaluating LinkedIn job-suggestion emails. That is the next step after this change: forward those mails from inbox triage, then fetch the jobs via the LinkedIn MCP and run this evaluator.

## Capabilities

### New Capabilities

- `preferences`: The preferences file format and the interview that writes it.
- `job-search`: Collecting postings via JobSpy into normalised records, with caps and deduplication against the tracking store.
- `job-evaluation`: The soft, digest-informed pre-filter that turns new postings into leads with a reason.
- `lead-review`: The user's accept/deny pass over leads, with optional reasons.

### Modified Capabilities

- `application-tracking`: the allowed statuses gain `to_apply` and `dismissed`.

## Impact

- New files:
  - `jobs/scrape.py` and `jobs/add_leads.py`
  - `.claude/agents/job-evaluator.md`
  - `.claude/skills/{grill-preferences,find-jobs,review-leads}/SKILL.md`
  - tests for normalisation, dedupe, digest and migration
- `tracking/schema.sql`: new status list, plus a migration step for existing DBs.
- Updated: `.claude/skills/update-tracking/SKILL.md` and CLAUDE.md.
- New dependency: `python-jobspy`, which pulls in pandas. Preferences are parsed with stdlib `tomllib`.
- Network access to job sites during `/find-jobs`.
