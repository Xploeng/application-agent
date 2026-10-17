# inbox-check Specification

## Purpose

Picks up application status changes from the user's email inbox on request. Mail is read without altering the mailbox, unrelated mail is filtered out cheaply, and the existing applications are updated automatically.

## Requirements

### Requirement: Mailbox is never modified
The inbox check MUST NOT change the mailbox in any way. It does not mark mail as read, change flags, move mail, or delete mail.

#### Scenario: Unread mail stays unread
- **WHEN** the inbox check runs over a mail that is unread
- **THEN** the mail is still unread afterwards

### Requirement: Only the message text is fetched
For each mail, the check SHALL fetch the headers needed for triage (date, sender, subject) and a single text body part: HTML if present, otherwise plain text. It MUST NOT download attachments or inline images. HTML MUST be converted to text without rendering it, so no remote content (such as tracking pixels) is requested.

#### Scenario: Mail with attachment
- **WHEN** a new mail has an HTML body and a PDF attachment
- **THEN** only the headers and the HTML body text are fetched, and the PDF is not downloaded

#### Scenario: Plain-text-only mail
- **WHEN** a new mail has no HTML part
- **THEN** its plain-text body is used

#### Scenario: Remote images in HTML
- **WHEN** a mail's HTML references remote images
- **THEN** no request is made to those image URLs

### Requirement: Only mail newer than the last run is read
The check SHALL store the received date of the newest mail it has processed, and SHALL read only mail received after that date on the next run. Nothing else about individual mails SHALL be stored. The stored date SHALL start at the moment the inbox check is installed, because tracking is up to date then. The user MAY give an explicit start date for a single run.

#### Scenario: Second run
- **WHEN** a run processed mail up to 2026-10-17T09:30 and the check runs again
- **THEN** only mail received after 2026-10-17T09:30 is fetched

#### Scenario: First run after installation
- **WHEN** the inbox check runs for the first time
- **THEN** only mail received after it was installed is fetched

#### Scenario: Stamp advances only after a completed run
- **WHEN** a run fails before applying its updates
- **THEN** the stored date is unchanged, and the next run reads the same mail again

### Requirement: Fetched content is temporary
Fetched mail content SHALL be written only to a temporary directory outside the project. That directory SHALL be deleted at the end of the run.

#### Scenario: After a run
- **WHEN** an inbox check finishes
- **THEN** no fetched mail content remains on disk, and none was ever written inside the project

### Requirement: Token-light triage that filters out noise
A small model SHALL triage new mail. It first decides from sender and subject alone, and reads a mail's body only when those are not enough. The triage SHALL have read-only access and MUST NOT be able to modify files, the store, or the mailbox. It SHALL return only mails relevant to job applications, each with: received date, company, role (if identifiable), kind (`confirmation`, `interview`, `rejection`, `offer`) and a one-line summary. Unrelated mail SHALL be discarded and not passed on.

#### Scenario: Newsletter
- **WHEN** a new mail is a newsletter whose subject makes clear it is unrelated
- **THEN** it is discarded without its body being read and does not appear in the triage output

#### Scenario: Unclear subject
- **WHEN** a mail's subject and sender do not show whether it concerns an application (e.g. "Ihre Nachricht")
- **THEN** the triage reads its body before deciding

#### Scenario: Rejection mail
- **WHEN** a new mail is a rejection from a company the user applied to
- **THEN** the triage output contains it with kind `rejection`, its received date, the company and a summary

### Requirement: Existing applications are updated automatically
Relevant mails SHALL be applied to matching existing applications in order of received date, oldest first, without asking for confirmation. Kinds map to statuses as follows: `confirmation` to `applied`, `interview` to `interview`, `rejection` to `rejected`, `offer` to `offer`. Each applied mail SHALL also be recorded as an event of kind `email` with source `inbox` and the summary. A `confirmation` SHALL also set the application's date applied to the mail's received date, if that field is empty.

#### Scenario: Rejection applied
- **WHEN** the triage returns a rejection for Initech and exactly one Initech application exists
- **THEN** that application's status becomes `rejected` and an `email` event with source `inbox` exists for it

#### Scenario: Confirmation of receipt
- **WHEN** the triage returns a confirmation dated 2026-10-15 for an existing Avelios application with status `lead` and no date applied
- **THEN** its status becomes `applied`, its date applied becomes 2026-10-15, and an `email` event with source `inbox` exists for it

#### Scenario: Confirmation does not overwrite a known date
- **WHEN** a confirmation arrives for an application whose date applied is already set
- **THEN** the date applied is unchanged

#### Scenario: Several mails for one application
- **WHEN** the triage returns a confirmation and, dated later, an interview invitation for the same application
- **THEN** the final status is `interview`

### Requirement: Unmatched mails are reported, never inserted
The inbox check MUST NOT create applications. A relevant mail that matches no application, or more than one, SHALL be listed in the end-of-run report and not written.

#### Scenario: Unknown company
- **WHEN** the triage returns an interview invitation from a company with no application
- **THEN** no application is created and the mail appears in the report

#### Scenario: Ambiguous company
- **WHEN** a relevant mail names a company with two applications and the role cannot be determined
- **THEN** nothing is written for it and it appears in the report

### Requirement: End-of-run report
Each run SHALL end with a short report: the number of mails fetched and discarded, the status changes applied, and the unmatched mails.

#### Scenario: Run summary
- **WHEN** a run fetched 120 mails, of which 3 were relevant, 2 were applied and 1 was unmatched
- **THEN** the report shows those counts, the 2 changes, and the 1 unmatched mail

### Requirement: Credentials stay out of the repository
Mail server host, user and password SHALL be read from a gitignored `.env` file and MUST NOT appear in committed files or in the output.

#### Scenario: Missing credentials
- **WHEN** `.env` is missing or lacks a required value
- **THEN** the check stops with a message naming the missing setting, and the mailbox is not contacted
