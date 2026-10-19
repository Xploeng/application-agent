## MODIFIED Requirements

### Requirement: Preferences file
The preferences SHALL live in one file outside version control. It has two parts, plus an optional third:

- a **Search** part that the scraper reads: search terms, locations with radius, maximum posting age, and the JobSpy sites to use,
- a **What I want** part in free text that the evaluator reads,
- an optional **Review** part: a list of short reasons that the tracking UI offers as checkboxes when reviewing leads.

#### Scenario: Scraper reads search settings
- **WHEN** a job search runs
- **THEN** it uses the search terms, locations, age window and sites from the file

#### Scenario: Missing file
- **WHEN** a job search starts and no preferences file exists
- **THEN** it stops and suggests running the preference interview

#### Scenario: Review reasons listed
- **WHEN** the file lists the review reasons "AI-adjacent" and "consulting" and the user opens the lead review
- **THEN** those two reasons are offered as checkboxes

#### Scenario: No review part
- **WHEN** the file has no review part, or no file exists
- **THEN** the lead review offers only free-text reasons, and the job search behaves as before
