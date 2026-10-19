## Purpose

Holds the facts about the user that applications draw on, in one personal file. A guided interview builds and refines it from the user's documents, LinkedIn profile, past letters and answers.

## ADDED Requirements

### Requirement: Profile file
The profile SHALL be a single human-editable file outside version control. It holds the user's facts for applications: education, experience, projects and concrete achievements, skills, languages, and motivations. It SHALL contain only what a source or the user confirmed.

#### Scenario: User edits by hand
- **WHEN** the user changes the profile file directly
- **THEN** the next letter and the next interview use the changed content

### Requirement: Profile interview sources
The profile interview SHALL read every document in the user's about-me folder, the user's own LinkedIn profile, and the sample cover letters before asking questions. If LinkedIn is unavailable, it SHALL say so and continue with the other sources.

#### Scenario: New document added
- **WHEN** the user adds a new document to the about-me folder and runs the interview
- **THEN** facts from that document are proposed for the profile

#### Scenario: LinkedIn unavailable
- **WHEN** the LinkedIn profile can't be read (server not running, session expired)
- **THEN** the interview reports it and builds the profile from the remaining sources

### Requirement: Interview questions
The interview SHALL ask the user one question at a time, about gaps, conflicts between sources, concrete examples behind claims, and motivations. Every question SHALL be skippable. Where sources disagree (for example different dates), it SHALL ask rather than choose.

#### Scenario: Conflicting dates
- **WHEN** the CV and LinkedIn give different end dates for the same position
- **THEN** the interview asks the user which is right

#### Scenario: Skipped question
- **WHEN** the user skips a question
- **THEN** the interview moves on and leaves that part of the profile as it was

### Requirement: User approves the profile
The interview SHALL show the resulting profile, or the changes to an existing one, and write it only after the user agrees. Running it again SHALL refine the existing profile rather than start over.

#### Scenario: Refinement run
- **WHEN** the user runs the interview while a profile exists
- **THEN** it starts from the current profile, asks only about what is new, missing or conflicting, and shows the changes before saving
