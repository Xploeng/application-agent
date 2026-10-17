## What Changes

Add a script and skill that scrape the job market using JobSpy.

## Planned scope (notes, to be detailed when this change is designed)

### Job-fit evaluator

Build an evaluator that decides, for a job posting, whether it fits the user's requirements and is worth applying to, or is something the user is not interested in. Every job source feeds the same evaluator:

```
  JobSpy scrape results ------+
                              |
  LinkedIn job-alert mails ---+--> job details --> evaluator --> fit: add as lead (with posting text)
  (job suggestions/proposals) |    (LinkedIn MCP:              no fit: skip
                              |     get_job_details)
  LinkedIn search (MCP) ------+
```

### LinkedIn job-suggestion emails as an input

The user receives many LinkedIn emails with job suggestions. Some match the user's requirements and some don't. These should be evaluated with the same evaluator:

- Extract the job IDs or links from the LinkedIn suggestion mail.
- Fetch each job's details through the LinkedIn MCP (`get_job_details`, from `add-linkedin-mcp`).
- Run the evaluator, and add the jobs that fit as `lead` applications with their posting text.

This depends on two things:

- **`add-linkedin-mcp`:** LinkedIn access and posting capture.
- **The inbox flow:** today the `inbox-triage` agent discards job-alert digests and "recommended jobs" mails as noise. To use them, the triage (or a separate step) must forward LinkedIn job-suggestion mails, or at least their job IDs, instead of dropping them. That needs a change to the `inbox-check` spec, which currently returns only application-status mails.
