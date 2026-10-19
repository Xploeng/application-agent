## What Changes

Evaluate the job suggestions in LinkedIn emails. Inbox triage forwards the job IDs instead of discarding these mails. Each job is fetched with the LinkedIn MCP (`get_job_details`) and run through the existing job evaluator, and the fits become leads.

Earlier planning notes: `git show 04fe08f:openspec/changes/add-job-scraper/proposal.md` (section "LinkedIn job-suggestion emails as an input"). Related specs: `inbox-check`, `job-evaluation`, `linkedin-access`.
