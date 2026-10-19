## Purpose

Softly pre-filters new postings against the user's preferences and past decisions. Clear mismatches are dropped, and everything plausible becomes a lead with a short reason, for the user to decide on.

## ADDED Requirements

### Requirement: Soft filter
The evaluator SHALL drop only postings that clearly do not fit the preferences, for example a different field, far too senior or junior, an unreachable location without remote work, or a required language the user does not speak. When in doubt it SHALL keep the posting.

#### Scenario: Borderline posting
- **WHEN** a posting partly matches (right field, unclear seniority)
- **THEN** it is kept as a lead

#### Scenario: Clear mismatch
- **WHEN** a posting is for an unrelated field (e.g. accounting)
- **THEN** it is dropped and does not reach the store

### Requirement: Decisions inform the filter as examples
The evaluator SHALL receive a digest of the user's past decisions, generated from the tracking store at each run:

- **liked:** applications with status `to_apply`, `applied`, `interview`, `offer` or `rejected` (the user applied in each case),
- **passed on:** applications with status `dismissed`, with the user's reason where one was given.

The digest SHALL be presented as examples, not rules, and limited to the most recent entries.

#### Scenario: Pattern from dismissals
- **WHEN** the user dismissed several consulting roles with the reason "consulting"
- **THEN** the evaluator sees these as examples when judging new consulting roles

#### Scenario: No decisions yet
- **WHEN** no applications have been dismissed
- **THEN** evaluation still runs, using the preferences and the liked examples

### Requirement: Token-light evaluation
The evaluator SHALL first judge from title, company and location. It SHALL read a posting's full description only when those are not enough. It SHALL have read-only access.

#### Scenario: Obvious misfit by title
- **WHEN** a posting's title is "Steuerfachangestellte/r"
- **THEN** it is dropped without its description being read

### Requirement: Kept postings become leads
Each kept posting SHALL be added to the store with status `lead`, its canonical URL, source (the JobSpy site), title, company, location, the full posting text and capture time, and a one-line evaluator reason recorded on the application.

#### Scenario: Lead added
- **WHEN** the evaluator keeps a posting with the reason "agentic platform team, Munich hybrid"
- **THEN** a `lead` exists with the URL, posting text and capture time, and the reason is visible with it
