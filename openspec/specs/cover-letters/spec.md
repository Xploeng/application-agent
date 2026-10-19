# cover-letters Specification

## Purpose

Writes a cover letter for one posting the user names, using the posting stored in the tracking store, the facts in the profile and the style of the user's own sample letters.

## Requirements

### Requirement: Explicit posting only
Letter writing SHALL work only on the posting the user names, by application id or company. It SHALL NOT choose a posting on its own. If no posting is named, it SHALL do nothing. If the name matches no application or more than one, it SHALL list the matches and stop. It SHALL write one letter per run.

#### Scenario: Nothing named
- **WHEN** letter writing starts without a posting
- **THEN** it writes nothing and says a posting must be named

#### Scenario: Ambiguous company
- **WHEN** the user names a company with two tracked applications
- **THEN** it lists both with id and role and stops without writing

### Requirement: Inputs and their roles
A letter SHALL be based on the posting text stored for the application. All claims about the user SHALL come from the profile. The sample letters SHALL guide only tone, length and structure, not facts. If the application has no stored posting text, or no profile exists, it SHALL say so and stop.

#### Scenario: No posting text
- **WHEN** the named application has no stored posting text
- **THEN** it stops and says the posting text must be captured first

#### Scenario: No profile
- **WHEN** no profile file exists
- **THEN** it stops and suggests running the profile interview

#### Scenario: Requirement not covered
- **WHEN** the posting asks for a skill that the profile does not mention
- **THEN** the letter does not claim it

### Requirement: Motivation and fit, not a CV recap
A letter SHALL open with a short motivation (two or three sentences) based on the role's core responsibility, weighing responsibilities as the posting does. The body SHALL use only the few profile facts that prove fit for the posting's main responsibilities, each tied to a responsibility. It SHALL NOT restate the CV (education history, generic lists of years and tools) unless the posting asks for it.

#### Scenario: Matching side task
- **WHEN** a posting's core is model training and one minor responsibility matches the user's main interest
- **THEN** the opening is about model training, and the minor responsibility is at most a supporting point

### Requirement: Feedback log
Letter writing SHALL follow the rules in the user's cover-letter feedback file, if one exists, over the style of the samples. When the user requests changes to a draft, the saved letter SHALL be followed by a new entry in that file with the feedback, the general rule behind it and the outcome. A rule already in the file SHALL NOT be added again.

#### Scenario: Rule from earlier feedback
- **WHEN** the feedback file says to keep the opening to two or three sentences
- **THEN** the next draft's opening has at most three sentences

#### Scenario: Feedback recorded
- **WHEN** the user asks for one round of changes and then approves
- **THEN** one entry with that feedback, its rule and the outcome is appended to the feedback file

#### Scenario: Approved without changes
- **WHEN** the user approves the first draft
- **THEN** the feedback file is unchanged

### Requirement: Posting language
A letter SHALL be written in the language of the posting.

#### Scenario: German posting
- **WHEN** the posting text is in German
- **THEN** the letter is written in German

### Requirement: Revision and saving
The user SHALL be able to request changes to the draft until satisfied. The final letter SHALL be saved as plain text in a generated-letters folder separate from the sample letters, named after the company. An existing file SHALL NOT be overwritten without asking. Letter writing SHALL never write to the sample folder.

#### Scenario: Approved letter
- **WHEN** the user approves the draft
- **THEN** it is saved in the generated-letters folder, and the sample folder is unchanged

#### Scenario: Existing letter for the company
- **WHEN** a generated letter for the same company already exists
- **THEN** the user is asked before it is overwritten

### Requirement: Tracking store is read-only
Letter writing SHALL NOT change the tracking store: no status changes, no notes, no new rows.

#### Scenario: Letter written
- **WHEN** a letter is saved for an application in status `to_apply`
- **THEN** the application's status and events are unchanged
