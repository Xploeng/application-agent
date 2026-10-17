# excel-import Specification

## Purpose

A one-time migration of the existing Excel tracking sheet into the tracking store. Claude guides it and the user approves the mapping, so historical applications are not lost when tracking moves off Excel.

## Requirements

### Requirement: Raw rows are staged before mapping
The import SHALL first copy every data row of the sheet into a staging area inside the store, keeping the original column names and cell values as text. It SHALL NOT write to the applications table at this point.

#### Scenario: Sheet staged
- **WHEN** the import reads a sheet with N data rows
- **THEN** the staging area holds N rows with the original values, and the applications table is unchanged

### Requirement: User approves the mapping before any insert
Claude SHALL propose a mapping from sheet columns to application fields and from the sheet's status values to the allowed statuses, and show it to the user with sample rows. No application SHALL be inserted until the user explicitly approves the mapping.

#### Scenario: Mapping approved
- **WHEN** the user approves the proposed mapping
- **THEN** the staged rows are inserted as applications according to that mapping

#### Scenario: Mapping rejected
- **WHEN** the user rejects or corrects the mapping
- **THEN** no applications are inserted and Claude presents a revised mapping

#### Scenario: Unmappable status
- **WHEN** a sheet status value has no clear match in the allowed statuses
- **THEN** Claude asks the user which status it maps to instead of guessing

### Requirement: Values are normalised
The import SHALL convert dates to ISO 8601 and map statuses to the allowed set. Values it cannot convert unambiguously (for example a date that could be day-first or month-first) MUST be shown to the user for a decision before insertion.

#### Scenario: Ambiguous date
- **WHEN** a staged row contains a date such as `03/04/2026` whose format cannot be told from the rest of the sheet
- **THEN** the user is asked how to read it before that row is inserted

### Requirement: Screenshot references are ignored
References to posting screenshots in the sheet SHALL NOT be imported. Imported applications SHALL have empty posting text and posting capture timestamp.

#### Scenario: Row with screenshot reference
- **WHEN** a staged row contains a screenshot reference
- **THEN** the imported application has no posting text, and the reference is not stored in any field

### Requirement: Import is all-or-nothing and traceable
The approved insert SHALL run as a single transaction: either every approved row is imported or none is. Each imported application SHALL get an event with source `excel-import`. The import SHALL NOT modify the Excel file.

#### Scenario: Failure mid-import
- **WHEN** a row fails to insert during the approved import (for example a duplicate URL)
- **THEN** no rows from that run are kept, and the failing row is reported to the user

#### Scenario: Successful import
- **WHEN** the approved import completes
- **THEN** the number of applications inserted equals the number of approved rows, each has an `excel-import` event, and the Excel file is byte-identical to before

### Requirement: Staging is cleaned up
After the user confirms the imported data, the staging area SHALL be removed from the store.

#### Scenario: User confirms import
- **WHEN** the user confirms the imported applications look correct
- **THEN** the staging area no longer exists in the store
