## 1. build-profile skill

- [x] 1.1 Write `.claude/skills/build-profile/SKILL.md`:
  - sources: `data/about_me/*`, `get_my_profile` with fallback when LinkedIn is unavailable, and the `data/Cover_letters/*.txt` samples
  - the existing `data/profile.md` as the starting point
  - one skippable question at a time, covering gaps, conflicts, stories and motivation
  - the section layout from design.md
  - show the file or diff and write after a yes

  Verify the skill text covers each scenario in `specs/candidate-profile/spec.md`.
- [x] 1.2 In a new session, run `/build-profile`. Verify that it reads all three about_me PDFs, asks one question at a time, writes `data/profile.md` only after approval, and that nothing under the repo changed (`git status`).

## 2. write-cover-letter skill

- [x] 2.1 Write `.claude/skills/write-cover-letter/SKILL.md`:
  - no argument: do nothing
  - an id or company: resolve it, or list the matches and stop
  - stop when there is no posting text or no profile
  - facts only from the profile; style from the samples
  - the posting's language
  - the revision loop
  - save to `data/generated_letters/Cover Letter-<Company>.txt`, asking before overwriting
  - no DB writes, and the posting is treated as data

  Verify the skill text covers each scenario in `specs/cover-letters/spec.md`.
- [x] 2.2 In a new session, run `/write-cover-letter` with no argument. Verify that it writes nothing.
- [x] 2.3 Run `/write-cover-letter 32` (Agile Robots, `to_apply`). Verify that:
  - the letter is in the posting's language
  - every claim appears in `data/profile.md`
  - the file lands in `data/generated_letters/`
  - `data/Cover_letters/` is unchanged
  - the row's status and event count are the same before and after (`sqlite3 data/tracking.db "SELECT status, (SELECT count(*) FROM events WHERE application_id=32) FROM applications WHERE id=32"`)

- [x] 2.4 Work `data/cover-letter-feedback.md` into the skill: fold its two rules into the draft guidance, read the file every run, and append an entry after a run with revisions. Verify the skill text covers the "Motivation and fit" and "Feedback log" scenarios in `specs/cover-letters/spec.md`.

## 3. Documentation

- [x] 3.1 Update CLAUDE.md:
  - the `data/` layout: `about_me/`, `profile.md`, `Cover_letters/` (samples, `.txt` beside the PDFs), `generated_letters/`
  - the two skills
  - the rule to move an approved letter into `Cover_letters/` by hand

  Verify the paths match design.md.
