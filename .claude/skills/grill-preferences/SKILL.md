---
name: grill-preferences
description: Interview the user about their job preferences and write data/preferences.toml, which drives find-jobs (JobSpy search settings) and the job evaluator (what they want). Use when the user wants to set up, change or refine their job preferences, or when find-jobs reports the preferences file is missing.
---

# Grill preferences

Write or refine `data/preferences.toml` by asking the user questions. The file is personal (gitignored).

## 1. Start from what is known

- **If the file exists,** read it. Every question starts from its current value ("Currently X. Keep?").
- **Read the user's history** (read-only):
  ```
  sqlite3 -box data/tracking.db "SELECT location, count(*) n FROM applications GROUP BY 1 ORDER BY n DESC"
  sqlite3 -box data/tracking.db "SELECT work_mode, focus, count(*) n FROM applications GROUP BY 1, 2 ORDER BY n DESC"
  sqlite3 -box data/tracking.db "SELECT role, company, status FROM applications ORDER BY updated_at DESC LIMIT 40"
  ```
  Dismissed jobs (status `dismissed`) and their `review` notes show what the user does **not** want.

## 2. Ask, one question at a time

- **Propose an answer from the data,** so the user mostly confirms or corrects. For example: "23 of your 28 jobs are in or near Munich. Search Munich + 50 km?"
- **Use AskUserQuestion when there are clear options,** plain chat otherwise. Every question can be skipped. Never insist; a skipped setting is left out, or keeps its current value.
- **Topics, in order:**
  1. Search area: cities and radius in km
  2. Job titles to search: these become `terms`. Seed them from the roles in the DB.
  3. Focus areas they want, and ones they don't
  4. Work mode: on-site, hybrid or remote, and how much travel
  5. Seniority and experience level
  6. Salary floor
  7. Company type and size (startup, corporate, research), and industries to avoid
  8. Languages they can work in
  9. Deal-breakers
  10. JobSpy sites. Default `indeed`, `linkedin`, `glassdoor`, `google`, which are the JobSpy sites that cover Germany. Google Jobs also pulls in many niche boards. `linkedin` here is anonymous guest search, not the user's account.
  11. Max posting age in days. Default 7, for weekly runs.

## 3. Write

Build the TOML in exactly this shape. Companies the user names as off-limits go into `exclude_companies` (keep existing entries). Topics 3 to 9 go into `want` as plain prose, written for the evaluator: what fits, what doesn't, and why.

```toml
[search]
terms = ["AI Engineer", "Machine Learning Engineer", "RL Engineer"]
locations = [{ name = "München", radius_km = 50 }]
max_age_days = 7
sites = ["indeed", "linkedin", "glassdoor", "google"]   # JobSpy site names
exclude_companies = ["Rheinmetall"]   # dropped before evaluation, whole-word match

[evaluator]
want = """
Applied ML, agentic systems or RL. Hybrid or flexible, Munich area, 70k+.
Not: pure BI/reporting, consulting body-leasing, roles needing 10+ years.
German and English are fine.
"""
```

1. Show the full file for a first run, or a diff against the current file. Ask "Save this?"
2. Only on yes, write `data/preferences.toml` and check that it parses:
   `uv run python -c "import tomllib; tomllib.load(open('data/preferences.toml','rb')); print('ok')"`
3. Tell the user they can run this again anytime to refine, and that `/find-jobs` uses it.
