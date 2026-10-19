---
name: build-profile
description: Build or refine data/profile.md, the user's facts for applications (education, experience, projects, stories, skills, motivation). Reads data/about_me/ (CV, transcript, ...), the user's LinkedIn profile and the sample cover letters, then asks the user questions one at a time. Use when the user wants to set up or update their profile, or when write-cover-letter reports the profile is missing.
---

# Build profile

Write or refine `data/profile.md`. Cover letters take their facts **only** from this file, so it must hold nothing that a source or the user didn't confirm. The file is personal (gitignored).

## 1. Read the sources

1. **Existing profile:** if `data/profile.md` exists, read it. This run refines it: ask only about what is new, missing or conflicting.
2. **Documents:** Read every file in `data/about_me/` (PDFs too). List them with `ls data/about_me/`.
3. **LinkedIn:** call `get_my_profile`. If it fails (Docker not running, session expired), tell the user in one line and carry on without it.
4. **Sample letters:** Read the `.txt` files in `data/Cover_letters/`, plus any PDF there that has no `.txt` beside it. They show which facts and stories the user already tells companies. They are a source of facts here, not of style.

## 2. Ask, one question at a time

- **Propose an answer from the sources,** so the user mostly confirms or corrects. For example: "Your CV says the thesis was on X and the Globex letter mentions a 30% speed-up. Is that the same project?"
- **Use AskUserQuestion when there are clear options,** plain chat otherwise. Every question can be skipped. A skipped topic stays as it is in the profile, or is left out.
- **Never resolve a conflict yourself.** When sources disagree (dates, titles, grades), ask which one is right.
- **What to ask about, in order:**
  1. Conflicts between sources
  2. Gaps: positions, dates or results that are missing or vague
  3. Stories: concrete achievements with a number or an outcome, for the main projects and positions. Ask "what came out of it?"
  4. Motivation: what kind of work they want and why, and what they want to grow into
  5. Anything else they always want a letter to be able to say (availability, relocation, work permit, ...)

## 3. Write

Use exactly these sections. Leave a section out when there's nothing for it. Keep entries short and factual: these are facts for letters, not prose.

```markdown
# Profile

## Basics
Name, location, contact line as used in letters, availability.

## Education
- 2021-2024 M.Sc. ..., University, grade, thesis: ...

## Experience
- 2023-2024 Role, Company: what they did, tech used

## Projects
- Name: what, how, result

## Stories
- Concrete achievement with a number or outcome, and its context

## Skills
Languages, frameworks, methods.

## Languages
German (native), English (C1), ...

## Motivation
What they want to work on and why.
```

1. Show the full file on a first run, or a diff against the current file. Ask "Save this?"
2. Only on yes, write `data/profile.md`.
3. Tell the user they can edit it by hand or run this again anytime, and that `/write-cover-letter` uses it.
