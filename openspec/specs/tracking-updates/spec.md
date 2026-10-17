# tracking-updates Specification

## Purpose

Lets the user update the application-tracking store in plain language during a Claude session: change a status, add an application, or add a note. Nobody has to write SQL by hand.

## Requirements

### Requirement: Status change on request
When the user asks to change an application's status, Claude SHALL identify the application by company (and role when needed) and set the new status. The status change is then recorded in the store's history.

#### Scenario: Clear match
- **WHEN** the user says "Globex invited me to an interview" and exactly one application exists for Globex
- **THEN** that application's status becomes `interview` and a `status_change` event exists for it

#### Scenario: Ambiguous match
- **WHEN** the user names a company that has more than one application and does not say which role
- **THEN** Claude asks which application is meant before writing anything

#### Scenario: Unknown application
- **WHEN** the user names a company with no application in the store
- **THEN** Claude says so and offers to add it instead of silently creating one

### Requirement: Add application on request
When the user asks to add an application, Claude SHALL insert it with at least company and role, plus any other fields the user gives (URL, location, posting text, status). The status defaults to `lead` unless the user states otherwise.

#### Scenario: New application with status
- **WHEN** the user says "I applied to Hooli as ML Engineer"
- **THEN** a new application for Hooli / ML Engineer with status `applied` exists

#### Scenario: Posting text given
- **WHEN** the user provides the posting text or a reachable posting URL while adding an application
- **THEN** the posting text and its capture time are stored on the application

### Requirement: Notes on request
When the user asks to note something about an application, Claude SHALL record it as an event of kind `note` with source `manual`, without changing the status.

#### Scenario: Note added
- **WHEN** the user says "note for Initech: recruiter is Ms. Huber"
- **THEN** a `note` event with that text exists for the Initech application and its status is unchanged

### Requirement: Store rules are respected
All writes SHALL go through the tracking store's normal access path, so its validation applies. A write the store rejects, such as an invalid status, MUST be reported to the user and not retried with altered data unasked.

#### Scenario: Rejected write
- **WHEN** a requested update violates a store rule
- **THEN** Claude reports the failure and the reason, and the store is unchanged

### Requirement: LinkedIn posting capture
When the user asks to add or save a LinkedIn job, given as a URL, a job ID, or a result from a LinkedIn search, Claude SHALL read the job's details through the LinkedIn tools. It SHALL then add the application with company, role, location, the job URL, source `linkedin`, status `lead` unless the user says otherwise, the full posting text, and the capture time. If the job's URL already exists in the store, Claude SHALL NOT add a duplicate. If that application has no posting text, Claude SHALL fill it in.

#### Scenario: Save a LinkedIn job
- **WHEN** the user says "save linkedin.com/jobs/view/4012345678"
- **THEN** a new application exists with the company, role and location from LinkedIn, source `linkedin`, status `lead`, the posting text, and a capture time

#### Scenario: Job already tracked
- **WHEN** the user saves a LinkedIn job whose URL is already stored on an application without posting text
- **THEN** no new application is created, and the existing one gets the posting text and capture time

#### Scenario: LinkedIn unavailable
- **WHEN** the LinkedIn tools fail (for example the session expired or Docker is not running)
- **THEN** Claude says so, and asks before adding the application without posting text
