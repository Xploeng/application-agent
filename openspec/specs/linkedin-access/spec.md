# linkedin-access Specification

## Purpose

Gives Claude read-only access to LinkedIn job postings and company pages, so it can search openings and read posting details. The server runs isolated from the user's machine, at a version the user controls.

## Requirements

### Requirement: Job search and details
In a session in this project, Claude SHALL be able to search LinkedIn jobs by keyword and location, read a job's full details, read company profiles, and list the user's saved jobs.

#### Scenario: Search then read
- **WHEN** the user asks Claude to find "ML Engineer" jobs in Munich on LinkedIn
- **THEN** Claude returns matching postings and can read the full description of any of them

### Requirement: Read-only tool set
Only read-only job and company tools SHALL be usable: `search_jobs`, `get_job_details`, `get_company_profile`, `search_companies`, `get_saved_jobs`, `get_my_profile`. Tools that act as the user or read private communication (sending messages, connection requests, inbox and conversations, feed, people and employee search, posts) MUST be blocked.

#### Scenario: Blocked action
- **WHEN** Claude attempts to call `send_message` or `connect_with_person`
- **THEN** the call is denied without reaching LinkedIn

#### Scenario: Allowed read
- **WHEN** Claude calls `get_job_details` for a job ID
- **THEN** the call runs without a permission prompt

### Requirement: Isolated, pinned server
The LinkedIn server SHALL run in a container that can access only its own session folder. It MUST run a fixed image version identified by digest, so new server code runs only after the user deliberately changes the pin.

#### Scenario: No access to local browser cookies
- **WHEN** the server starts
- **THEN** it has no access to the user's home directory or local browser profiles, only to its mounted session folder

#### Scenario: Upstream release
- **WHEN** a new server version is published
- **THEN** sessions keep running the pinned version until the configuration is changed

### Requirement: Persistent login outside the repository
The LinkedIn session SHALL be created once by an interactive login. It SHALL persist across sessions in a folder outside the repository, and MUST NOT be committed.

#### Scenario: Next session
- **WHEN** the user starts a new Claude session after logging in once
- **THEN** LinkedIn tools work without logging in again, until LinkedIn expires the session
