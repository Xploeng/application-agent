## Purpose

Lets the user go through open leads one at a time with enough detail to decide: apply (application outstanding), not (denied, optionally saying why), or later.

## ADDED Requirements

### Requirement: One lead at a time
On request, Claude SHALL present open leads (status `lead`) one at a time. For each, it shows the lead and then an interactive choice: apply, no, skip for now, or stop reviewing. After an answer it SHALL move straight on to the next lead. A list of all leads at once SHALL NOT be shown.

#### Scenario: Review session
- **WHEN** the user asks to review leads and 5 leads exist
- **THEN** Claude shows lead 1 of 5 with its posting and choices, and shows lead 2 only after the user has answered

#### Scenario: Nothing to review
- **WHEN** no leads exist
- **THEN** Claude says so

### Requirement: Lead shown with its full posting
Each lead SHALL be shown with company, title, location, site, the date it was found, the URL and the evaluator's reason, followed by the full stored posting text, unsummarised and unchanged.

#### Scenario: Lead with posting text
- **WHEN** a lead with stored posting text is shown
- **THEN** the complete posting text appears below its header

#### Scenario: Lead without posting text
- **WHEN** a lead has no stored posting text
- **THEN** Claude says so and points to the URL

### Requirement: Decisions
Choosing apply SHALL set the lead to `to_apply`. Choosing no SHALL set it to `dismissed`. Skip SHALL leave it as `lead`, so it comes up again in a later review. Stop SHALL end the session and leave all remaining leads as `lead`.

#### Scenario: Mixed session
- **WHEN** the user answers apply for lead 1, no for lead 2, skip for lead 3, and then stops
- **THEN** lead 1 is `to_apply`, lead 2 is `dismissed`, and lead 3 and all later leads are still `lead`

### Requirement: Optional reasons
A reason MAY accompany any decision, typed as free text together with the answer (e.g. "no, consulting"). It is never required, and Claude SHALL NOT ask for it in a separate step. When given, it SHALL be recorded on the application, so later evaluations can use it.

#### Scenario: Reason given
- **WHEN** the user answers "no, consulting" for a lead
- **THEN** the lead is `dismissed` and "consulting" is recorded as the reason

#### Scenario: No reason
- **WHEN** the user chooses no without adding anything
- **THEN** the lead is `dismissed`, no reason is recorded, and Claude does not ask for one
