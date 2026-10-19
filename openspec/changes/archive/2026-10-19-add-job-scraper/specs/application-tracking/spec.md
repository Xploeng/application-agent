## MODIFIED Requirements

### Requirement: Allowed statuses
An application's status MUST be one of: `lead`, `to_apply`, `applied`, `interview`, `offer`, `rejected`, `withdrawn`, `ghosted`, `dismissed`. `to_apply` means the user wants to apply ("application outstanding"). `dismissed` means the user decided against the job, which is distinct from `rejected` (the company said no). The store SHALL reject any other value, whatever tool performs the write.

#### Scenario: Invalid status
- **WHEN** a tool sets an application's status to a value outside the allowed set (e.g. `rejectd`)
- **THEN** the write is rejected and the previous status is kept

#### Scenario: New lead
- **WHEN** a tool inserts an application with status `lead`
- **THEN** the application is stored with status `lead`

#### Scenario: User accepts a lead
- **WHEN** a lead's status is set to `to_apply`
- **THEN** the write succeeds and a `status_change` event `lead -> to_apply` is recorded

#### Scenario: Existing store gains the new statuses
- **WHEN** the store is initialised over a database created before `to_apply` and `dismissed` existed
- **THEN** both statuses become valid, and all existing applications and events are preserved unchanged
