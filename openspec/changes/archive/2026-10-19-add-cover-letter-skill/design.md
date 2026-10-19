## Context

See proposal.md for motivation and specs/ for behaviour. What already exists:

- **Tracking store:** `applications.posting_text` holds the posting. It is read with the `sqlite3` CLI, as the other skills do.
- **LinkedIn MCP:** `get_my_profile` is already allowed in `.claude/settings.json`.
- **grill-preferences:** sets the interview pattern. It starts from what is known, asks one skippable question at a time, shows the file or diff, and writes after a yes.
- **`data/` (gitignored):**
  - `about_me/` holds `CV.pdf`, `CV-joined.pdf` and a transcript PDF.
  - `Cover_letters/` holds 7 samples, each as `.txt` (5 extracted from Canva PDFs, which sit next to them). 2 are in German and 5 in English.

## Goals / Non-Goals

**Goals:**

- Two `SKILL.md` files and nothing else. No scripts, because every step is a read, a conversation or one file write.
- Every claim in a letter can be traced to `data/profile.md`.

**Non-Goals:**

- No PDF or Canva output. The user pastes the text into their template or an application form.
- No batch mode and no automatic follow-up from review-leads.
- No status or note in the DB for "letter written". The file in `data/generated_letters/` is the record.

## Decisions

### Paths

```
data/about_me/*            input to build-profile (any file type Read handles)
data/profile.md            output of build-profile, input to write-cover-letter
data/Cover_letters/*.txt   samples: read by both skills, written by neither
data/generated_letters/    output of write-cover-letter
  Cover Letter-<Company>.txt   (same naming as the samples, so approving one is a plain move)
data/cover-letter-feedback.md  read by write-cover-letter, appended after a run with revisions
```

### Feedback file as the learning loop

Each entry holds the user's objection and a general "Rule for the skill". The writer reads the file every run, so a correction takes effect in the next letter without editing the skill. Rules that hold up get folded into `SKILL.md` by hand, as the first two were (motivation over CV recap, a short opening based on the core responsibility). The file stays in `data/` because it quotes the user's applications.

`generated_letters/` sits beside `Cover_letters/`, not inside it, so a draft can't become a sample by accident.

### Profile is markdown with fixed sections

The sections are Basics, Education, Experience, Projects, Skills, Languages, Stories and Motivation. **Stories** are concrete achievements with numbers or results, which is what a letter needs most and a CV usually lacks. Markdown, not TOML: it is prose for Claude and the user to read, and nothing parses it.

Alternative: no profile, so the writer reads the CV each time. That was rejected because the CV has no stories or motivations, the answers from the interview would be lost, and conflicts would be decided again in every run.

### The writer reads the samples directly

The writer reads all samples every time instead of a style summary inside the profile, because a summary loses the voice. Seven letters of about 300 words each is cheap. Samples in the posting's language count most for phrasing.

### PDFs are read with the Read tool

Both skills read PDFs with the Read tool, so nothing needs to be installed. The one-off `.txt` extraction of the samples was done with `uv run --with pypdf` and is not part of the skills. A sample that exists only as a PDF is read as a PDF.

### Resolving the named posting

The argument can be a number (application id) or a company. A company is matched with `company LIKE '%<name>%'`, in any status. Exactly one match proceeds. Otherwise the skill lists the matches and stops (spec: Explicit posting only).

## Risks / Trade-offs

- [The letter overstates the user's skills to match the posting] → The facts-from-profile-only rule.
- [Instructions planted in the posting text] → The posting is data, and any instructions in it are ignored. This is the same exposure as review-leads.
- [Approved generated letters become samples, so the style drifts toward Claude's voice] → The user only moves letters they edited or fully agree with. That is their call, not the skill's.
- [The LinkedIn session is often expired] → build-profile continues without it (spec), and the CV is the main source anyway.
