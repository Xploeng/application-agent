## Why

Writing a cover letter for each job takes the most time per application. The user already has seven letters that show their voice, plus a CV, a transcript and a LinkedIn profile. A letter written from the posting, the user's facts and their own past letters only needs a final edit. The facts have to come from one curated source, so the letters never claim anything the user can't back up.

## What Changes

- New skill **build-profile**. It reads everything in `data/about_me/` (CV, transcript, ...), the user's LinkedIn profile (`get_my_profile`) and the sample letters in `data/Cover_letters/`. Then it asks the user questions one at a time about gaps, concrete stories and motivations, and writes `data/profile.md` after the user approves. A later run refines the existing profile.
- New skill **write-cover-letter**. It writes one letter, for one posting the user names (an application id or company), using the posting text from the DB:
  - If no posting is named, it does nothing.
  - It never picks a posting by itself and never writes to the DB.
  - Facts come from `data/profile.md`, and style comes from the sample letters.
  - The letter is in the posting's language.
  - The user revises it in the main session. The result is saved to `data/generated_letters/`, apart from the samples, and the user moves it into `data/Cover_letters/` if they approve it.
- Already done during exploration: the five Canva PDF samples now have extracted `.txt` copies next to them, so every sample can be read as text.

## Capabilities

### New Capabilities
- `candidate-profile`: the user's profile file (facts for applications), and the interview that builds and refines it from documents, LinkedIn, past letters and the user's answers.
- `cover-letters`: writing a cover letter for one named posting from the profile and sample letters, in the posting's language, saved apart from the samples.

### Modified Capabilities
None. The skill only reads the tracking store. `get_my_profile` is already on the LinkedIn allow list.

## Impact

- New files: `.claude/skills/build-profile/SKILL.md` and `.claude/skills/write-cover-letter/SKILL.md`. No Python, no new dependencies.
- `CLAUDE.md`: document the profile, the sample and generated letter folders, and the two skills.
- Personal data (gitignored, under `data/`): `about_me/` (input), `profile.md` (new), `Cover_letters/` (samples, read-only for the skills) and `generated_letters/` (new output).
- Posting text, CV and letters are read in the main session. Posting text is already shown there by review-leads, and the CV and letters are the user's own.
