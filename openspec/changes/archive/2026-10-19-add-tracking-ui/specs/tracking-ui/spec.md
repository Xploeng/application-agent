## Purpose

A local web UI for the tracking store: browse all applications and their postings read-only, and review open leads one at a time without Claude, writing the decisions back in one batch.

## ADDED Requirements

### Requirement: Local only
The UI SHALL be reachable only from the local machine, and SHALL answer only requests addressed to a local host name, so that a website open in the browser can neither read the store nor, through a JSON-only write API, submit a review on the user's behalf.

#### Scenario: Other host
- **WHEN** another machine on the network connects to the UI's port
- **THEN** the connection is refused

#### Scenario: Foreign host name
- **WHEN** a request arrives whose Host header is not `127.0.0.1` or `localhost` (e.g. a DNS-rebinding page)
- **THEN** it is rejected without returning data

#### Scenario: Form post from another site
- **WHEN** a request to apply decisions arrives with a non-JSON body
- **THEN** it is rejected and the store is unchanged

### Requirement: Applications table
The UI SHALL list every application in a table with its status (colour-coded, one colour per status), role, company and the posting URL as a link that opens in a new tab. The table SHALL have one toggle per status, all on at first; turning a status off hides its applications. The status and URL columns SHALL be only as wide as their content, always showing the full status and host name, and status colours SHALL be readable in light and dark mode. It SHALL NOT allow editing.

#### Scenario: Table shown
- **WHEN** the user opens the UI and the store holds 114 applications
- **THEN** all 114 are listed with status, role, company and URL

#### Scenario: Filter by status
- **WHEN** the user turns off `dismissed` and `rejected`
- **THEN** all applications except dismissed and rejected ones are listed

#### Scenario: No URL
- **WHEN** an application has no URL
- **THEN** its URL cell is empty and the row still opens the detail view

### Requirement: Detail view
Selecting an application SHALL open a read-only detail view with company, role, location, source, the date the posting was captured, the URL, status and the evaluator's latest reason at the top, followed by the full posting text rendered as markdown. Rendering SHALL work without internet access.

#### Scenario: Posting rendered
- **WHEN** the user opens an application whose posting text contains markdown headings, bold text and lists
- **THEN** they are shown as formatted headings, bold text and lists, with no text left out

#### Scenario: No posting text
- **WHEN** the application has no stored posting text
- **THEN** the view says so and points to the URL

### Requirement: One lead at a time
The review SHALL show open leads (status `lead`), oldest first, one at a time, in the detail view layout with a position indicator (e.g. "Lead 3 of 70"). The decisions SHALL be apply, dismiss and skip, each available as a button and a single key (Y, N, S). After a decision the next lead SHALL be shown straight away. When no leads are open the review SHALL say so.

#### Scenario: Decide and advance
- **WHEN** the user presses Y on lead 3 of 70
- **THEN** lead 4 of 70 is shown

#### Scenario: Nothing to review
- **WHEN** the user opens the review and no leads exist
- **THEN** it says there are no leads to review

#### Scenario: Typing a reason
- **WHEN** the user types "n" into the free-text reason field
- **THEN** it is entered as text and is not taken as a decision

### Requirement: Undo
The review SHALL let the user take back the most recent decision not yet applied (button and key U). The lead it belonged to SHALL be shown again, with no decision recorded for it. Undo SHALL be repeatable back to the first pending decision.

#### Scenario: Undo a dismiss
- **WHEN** the user dismisses lead 5, then presses U
- **THEN** lead 5 is shown again and no decision is pending for it

### Requirement: Optional reasons
An apply or dismiss decision MAY carry a reason, given by ticking any number of reason checkboxes and/or typing free text. A skip means "not now" and SHALL never carry a reason: anything ticked or typed is discarded when skipping. The checkboxes SHALL be the reasons listed in the preferences file. When the file lists none, only the free-text field is shown. A reason SHALL never be required. When given, the ticked reasons and the free text SHALL be recorded together as one review note on the application.

#### Scenario: Ticked and typed
- **WHEN** the user ticks "AI-adjacent" and "boring use case", types "also too senior" and dismisses
- **THEN** after applying, the application is `dismissed` and has one review note containing all three

#### Scenario: No reason
- **WHEN** the user dismisses without ticking or typing anything
- **THEN** after applying, the application is `dismissed` and no review note is added

#### Scenario: Reason typed, then skipped
- **WHEN** the user types a reason and then skips
- **THEN** the reason is discarded, nothing is written for that lead, and it stays `lead`

### Requirement: Decisions held until applied
Decisions SHALL NOT change the store while reviewing. They SHALL be kept as pending decisions that survive a page reload or a server restart. Leaving the page with pending decisions SHALL ask for confirmation. A skip writes nothing, so it SHALL NOT count as a decision to write; skipped leads appear again in the next review. When every lead is decided and only skips are pending, the review SHALL offer to show the skipped leads again.

#### Scenario: Reload mid-review
- **WHEN** the user has made 10 decisions and reloads the page
- **THEN** the 10 decisions are still pending and the review continues after them

#### Scenario: Only skips
- **WHEN** the user skips every lead
- **THEN** the write counter stays at 0 and the review offers to show the skipped leads again

#### Scenario: Store untouched while reviewing
- **WHEN** the user has made decisions but not applied them
- **THEN** the statuses in the store are unchanged

### Requirement: Apply decisions in one go
The user SHALL be able to apply pending decisions at any time, and SHALL be offered to when the last lead is decided. Before applying, the UI SHALL show a summary: counts of apply, dismiss and skip, and the leads marked to apply. Applying SHALL write all decisions in a single transaction: apply sets `to_apply`, dismiss sets `dismissed`, and reasons are added as review notes. If the write fails, nothing SHALL be written and the decisions SHALL stay pending. After a successful apply, the pending decisions SHALL be cleared and the result shown.

#### Scenario: Mixed batch
- **WHEN** the user applies yes for lead 1, no with reason "consulting" for lead 2, and skip for lead 3
- **THEN** lead 1 is `to_apply`, lead 2 is `dismissed` with a review note "consulting", and lead 3 is still `lead`

#### Scenario: Write fails
- **WHEN** applying fails, e.g. because the store is locked
- **THEN** no decision is written, an error is shown, and all decisions are still pending

### Requirement: Changed leads are not overwritten
Applying SHALL only change applications that are still `lead`. A decision for an application whose status changed since the review started (e.g. by the inbox check) SHALL be skipped together with its reason, and reported to the user as a conflict. The other decisions SHALL still be applied.

#### Scenario: Lead moved by the inbox check
- **WHEN** the user dismisses a lead, and before applying the inbox check sets it to `applied`
- **THEN** applying leaves it `applied`, adds no note to it, applies the other decisions, and lists it as a conflict
