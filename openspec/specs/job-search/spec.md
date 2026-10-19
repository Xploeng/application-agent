# job-search Specification

## Purpose

Collects job postings that match the user's search preferences through JobSpy, and reduces them to new, unique postings before any model looks at them.

## Requirements

### Requirement: JobSpy sites
The job search SHALL collect postings through JobSpy from the sites enabled in the preferences. The default is the JobSpy sites that cover Germany: Indeed, LinkedIn guest search, Glassdoor, and Google Jobs, which also aggregates niche boards. It MUST NOT use the user's logged-in LinkedIn session. A site that fails SHALL be reported, and the other sites SHALL still run.

#### Scenario: One site down
- **WHEN** one site errors during a run
- **THEN** postings from the other sites are still returned, and the failed site is named in the run summary

#### Scenario: Sites from preferences
- **WHEN** the preferences list only `indeed` and `google`
- **THEN** only those two sites are queried

### Requirement: Normalised postings
Every posting SHALL be returned in one shape: site, title, company, location, URL, posting date (if known) and full description text (if available). URLs of known platforms SHALL be normalised to one canonical form per job, so the same job always has the same URL.

#### Scenario: Tracking parameters
- **WHEN** a site returns a job URL with tracking parameters
- **THEN** the stored URL is the canonical form without them

### Requirement: Caps and age window
A run SHALL collect at most 50 postings per search term per site, and SHALL keep only postings within the age window from the preferences.

#### Scenario: Cap reached
- **WHEN** a site has 200 matches for a search term
- **THEN** at most 50 are collected from that site for that term

### Requirement: Only new, unique postings
Before evaluation, the job search SHALL drop:

- postings whose URL already exists in the tracking store, whatever their status (including `dismissed`),
- duplicates of the same job found on several sites (same company and title).

#### Scenario: Previously dismissed job
- **WHEN** a posting the user dismissed last week is found again
- **THEN** it is dropped before evaluation

#### Scenario: Same job on two sites
- **WHEN** the same company and title arrive from two sites in one run
- **THEN** only one is passed on, preferring the one with the longer description
