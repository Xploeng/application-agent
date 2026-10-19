## 1. Status migration

- [x] 1.1 Update the status `CHECK` in `tracking/schema.sql` and add the one-off rebuild to `init()` as in design.md; verify with a unittest that an old-schema DB with rows and events migrates (row and event counts equal, ids kept, `to_apply`/`dismissed` accepted, invalid status still rejected, status trigger still fires) and that a second `init()` does nothing
- [x] 1.2 Back up and migrate the real DB with `uv run python -m tracking.db`; verify `data/tracking-pre-migration.db` exists, 28 applications and all events are intact, and `uv run python -m unittest discover tests` passes
- [x] 1.3 Add `to_apply` and `dismissed` (with meanings) to `.claude/skills/update-tracking/SKILL.md`; verify the status list matches the schema

## 2. Preferences

- [x] 2.1 Write `.claude/skills/grill-preferences/SKILL.md` (DB patterns first, one skippable question at a time, JobSpy sites, show TOML/diff, write after yes, `tomllib` check); verify the format it describes matches design.md and parses with `tomllib`
- [x] 2.2 User runs `/grill-preferences`; verify `data/preferences.toml` exists, loads with `tomllib`, and is gitignored

## 3. Sources and scraper

- [x] 3.1 ~~Spike for custom sources~~: done, then dropped. The scraper is JobSpy-only (user decision), so no custom APIs are used
- [x] 3.2 `uv add python-jobspy`; JobSpy call (one per term/location/site, isolated failures) and canonical URLs in `jobs/scrape.py`; verify with unittests on a mocked `scrape_jobs` DataFrame (incl. NaN values) for normalisation and canonical URLs
- [x] 3.3 Write `jobs/scrape.py` (preferences load, caps, age window, URL-in-DB and in-run dedupe, temp-dir output, digest into `context.md`, per-source summary); verify with unittests for dedupe (DB URL incl. dismissed, cross-source keep-longest) and digest content (liked/passed-on, reasons, limit)
- [x] 3.4 Run `uv run jobs/scrape.py` against the real preferences; verify each enabled site reports a count or a named failure and the temp dir contains `jobs.json`, `context.md` and one `.txt` per job

## 4. Evaluation and leads

- [x] 4.1 Write `.claude/agents/job-evaluator.md` (haiku, Read only, soft-keep instructions, title-first, JSON output) and `jobs/add_leads.py` (stdin JSON → `lead` rows with posting text from files + `evaluator` note events); verify `add_leads.py` with a unittest on a temp dir and temp DB
- [x] 4.2 Write `.claude/skills/find-jobs/SKILL.md` (flow, never Read the job files in main context, cleanup, report); verify in a new session that `/find-jobs` adds leads with URL, posting text and an evaluator reason, and the temp dir is gone

## 5. Review

- [x] 5.1 Write `.claude/skills/review-leads/SKILL.md` (one lead at a time: header with evaluator reason + full posting text, AskUserQuestion yes/no/skip/stop, optional reason as `review` note); verify in a session that answering yes, no + reason, skip, stop gives `to_apply`, `dismissed` + one `review` note, and leaves the rest as `lead`
- [x] 5.2 Run `/find-jobs` again after the review; verify the dismissed jobs are not re-added and `context.md` lists them with the reason

## 6. Documentation

- [x] 6.1 Update CLAUDE.md (preferences file, the three skills, `jobs/` scripts, new statuses, migration backup); verify listed commands run as written
