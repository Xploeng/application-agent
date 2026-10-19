## Status: Abandoned (2026-10-19)

Not built. The job-suggestion emails come from Indeed ("recommended jobs"), not LinkedIn. They don't match the user's profile well, and they surface nothing that find-jobs' Indeed search doesn't already catch, so there's no need to scan them separately.

Findings from exploration, in case this comes up again:

- `inbox/fetch.py` converts HTML to text and drops links, so job IDs/keys in alert mails never reach triage. Extraction would have to happen in `fetch.py` on the raw HTML.
- JobSpy reads Indeed only through its GraphQL search API; it has no lookup by job key, and `viewjob?jk=` pages are behind Cloudflare.

## What Changes (original plan)

Evaluate the job suggestions in LinkedIn emails. Inbox triage forwards the job IDs instead of discarding these mails. Each job is fetched with the LinkedIn MCP (`get_job_details`) and run through the existing job evaluator, and the fits become leads.

Earlier planning notes: `git show 04fe08f:openspec/changes/add-job-scraper/proposal.md` (section "LinkedIn job-suggestion emails as an input"). Related specs: `inbox-check`, `job-evaluation`, `linkedin-access`.
