# preferences Specification

## Purpose

Holds the user's job preferences in one personal file, used both for searching and for evaluating postings. A guided interview creates and refines it.

## Requirements

### Requirement: Preferences file
The preferences SHALL live in one file outside version control. It has two parts:

- a **Search** part that the scraper reads: search terms, locations with radius, maximum posting age, and the JobSpy sites to use,
- a **What I want** part in free text that the evaluator reads.

#### Scenario: Scraper reads search settings
- **WHEN** a job search runs
- **THEN** it uses the search terms, locations, age window and sites from the file

#### Scenario: Missing file
- **WHEN** a job search starts and no preferences file exists
- **THEN** it stops and suggests running the preference interview

### Requirement: Preference interview
A preference interview SHALL ask the user questions one at a time to fill in the preferences. It SHALL open with patterns found in the tracking store (locations, work modes, focus areas, roles), so the user can confirm them rather than state everything from scratch. Every question SHALL be skippable.

#### Scenario: Grounded first question
- **WHEN** the interview starts and the store holds applications that are mostly in one city
- **THEN** an early question proposes that city as the search area for the user to confirm or change

#### Scenario: Skipped question
- **WHEN** the user skips a question
- **THEN** the interview moves on and the file omits or keeps that setting

### Requirement: User approves the file
The interview SHALL show the resulting preferences, or the changes to an existing file, and write them only after the user agrees. Running it again SHALL refine the existing file rather than start over.

#### Scenario: Refinement run
- **WHEN** the user runs the interview while a preferences file exists
- **THEN** questions start from the current settings, and the user sees the changes before they are saved
