# application-tracking Specification

## Purpose

A single local store of job applications and their history, shared by every agent tool (scraper, update skill, inbox check) as the source of truth for application status.

## Requirements

### Requirement: Local store initialisation
The system SHALL keep all tracking data in one local database file at a fixed location inside the project. Initialisation SHALL create the file and its tables when they are missing, and SHALL leave existing data untouched when run again.

#### Scenario: First use
- **WHEN** initialisation runs and no database file exists
- **THEN** the file is created with empty `applications` and `events` tables

#### Scenario: Repeated initialisation
- **WHEN** initialisation runs against a database that already holds applications
- **THEN** all existing rows remain unchanged

### Requirement: Store is excluded from version control
The database file and its side files (write-ahead log, shared memory, journal) MUST be ignored by git, because they contain personal data.

#### Scenario: Database present in working tree
- **WHEN** the database file exists and `git status` is run
- **THEN** neither the database file nor its side files are listed as untracked

### Requirement: Application record
Each application SHALL record: company, role, posting URL, location, desired start date, work mode (e.g. hybrid, on-site), focus area, pay (free text), source, status, date applied, last-updated timestamp, notes, posting text and posting capture timestamp. Company and role MUST be present. The URL is optional, but when present it MUST be unique across applications. Dates and timestamps SHALL be stored as ISO 8601 text.

#### Scenario: Missing required field
- **WHEN** a tool inserts an application without a company or without a role
- **THEN** the insert is rejected and nothing is stored

#### Scenario: Duplicate URL
- **WHEN** a tool inserts an application whose URL already belongs to another application
- **THEN** the insert is rejected and the existing application is unchanged

#### Scenario: Application without URL
- **WHEN** a tool inserts an application with company and role but no URL
- **THEN** the application is stored

### Requirement: Allowed statuses
An application's status MUST be one of: `lead`, `applied`, `interview`, `offer`, `rejected`, `withdrawn`, `ghosted`. The store SHALL reject any other value, whatever tool performs the write.

#### Scenario: Invalid status
- **WHEN** a tool sets an application's status to a value outside the allowed set (e.g. `rejectd`)
- **THEN** the write is rejected and the previous status is kept

#### Scenario: New lead
- **WHEN** a tool inserts an application with status `lead`
- **THEN** the application is stored with status `lead`

### Requirement: Posting text capture
The system SHALL store the full text of a job posting in the application record, together with the time it was captured, so the posting survives removal from the job site. Both fields MAY be empty when no text is available.

#### Scenario: Posting captured
- **WHEN** a tool stores an application together with its posting text
- **THEN** the posting text and a capture timestamp are stored on the application

#### Scenario: Posting unavailable
- **WHEN** an application is stored without posting text
- **THEN** the posting text and capture timestamp are empty and the application is still stored

### Requirement: Status history
Every change of an application's status SHALL be recorded as an event holding the application, the time, the old and new status, and optionally its source (e.g. `manual`, `inbox`, `excel-import`). Tools MAY add further events of kind `email` or `note`. Events SHALL be append-only: normal operation never updates or deletes them.

#### Scenario: Status changes
- **WHEN** an application's status changes from `applied` to `rejected`
- **THEN** a `status_change` event recording `applied -> rejected` and the time of the change exists for that application

#### Scenario: Status write with the same value
- **WHEN** an application's status is set to the value it already has
- **THEN** no `status_change` event is recorded

#### Scenario: Event for unknown application
- **WHEN** a tool adds an event that references an application that does not exist
- **THEN** the event is rejected

### Requirement: Safe concurrent access
The store SHALL allow one tool to write while another reads or writes, for example the inbox check running while Claude edits records. A writer that finds the store busy SHALL wait briefly and retry instead of failing at once. No write SHALL be lost or partially applied.

#### Scenario: Two writers at once
- **WHEN** two tools write to the store at the same time
- **THEN** both writes are applied completely, one after the other
