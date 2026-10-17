## ADDED Requirements

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
