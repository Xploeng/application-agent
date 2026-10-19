---
name: find-jobs
description: Search job boards via JobSpy (Indeed, LinkedIn guest search, Glassdoor, Google Jobs) for new postings matching the user's preferences, softly filter them with the job-evaluator agent, and add the fits as leads with posting text. Use when the user asks to find, search or scrape jobs, or for their weekly job search.
---

# Find jobs

The pipeline: scrape with JobSpy, filter in a script (no tokens), evaluate with the `job-evaluator` subagent (Haiku), then insert leads. Posting text never enters the main session. Scripts move it from source to temp files to the DB.

## 1. Scrape

```
uv run jobs/scrape.py
```

- **If it says "No preferences":** suggest `/grill-preferences` and stop.
- **It can take several minutes,** because the boards are scraped with full descriptions. Use a generous timeout.
- **Output:**
  ```
  dir: <tmp>
  sites: indeed: 37; linkedin: 22; glassdoor: FAILED (...)
  collected: <n>
  new: <k>
  ```
  Remember `dir` and the sites line.
- **If `new: 0`,** report the sites line, `rm -r <tmp>`, and stop.

## 2. Evaluate

Spawn the `job-evaluator` agent with the prompt `Evaluate the jobs in <tmp>`.

- **Do not Read `jobs.json`, `context.md` or the `.txt` files yourself.**
- **Its reply is a JSON array** of `{id, reason}` for the kept jobs. Check that it parses as JSON. If it isn't valid JSON, ask the agent once more for only the array.

## 3. Insert leads

Pass the agent's array through unchanged, on stdin:

```
uv run jobs/add_leads.py <tmp> <<'EOF'
<the JSON array>
EOF
```

It prints `added: <n>` and any `skipped ...` lines (for example, already tracked).

## 4. Finish

1. `rm -r <tmp>`. Also do this if an earlier step failed.
2. Report:
   ```
   Sites:  indeed 37, linkedin 22, google 15, glassdoor FAILED
   New postings: 64 -> kept 18, dropped 46 by the evaluator
   Added 18 leads. Run /review-leads to go through them.
   ```

If a site keeps failing across runs, mention it. The user can remove it from `sites` in `data/preferences.toml`.
