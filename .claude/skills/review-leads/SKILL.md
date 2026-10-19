---
name: review-leads
description: Go through open job leads with the user one at a time, showing each lead's full posting, and record their decision - apply ("application outstanding", status to_apply), no ("denied", status dismissed, optional reason), or skip for now. Use when the user wants to review, go through or decide on leads or found jobs.
---

# Review leads

Show **one lead at a time**, ask, apply the answer, then show the next. Write through `uv run python -m tracking.db sql`, following the `update-tracking` rules.

## 1. Load the queue

```
sqlite3 -separator ' | ' data/tracking.db "SELECT id FROM applications WHERE status = 'lead' ORDER BY id"
```

- **If there are no rows,** say "No leads to review" and stop.
- **Otherwise** say how many leads are waiting, then start with the first.

## 2. For each lead

1. **Load it:**
   ```
   sqlite3 -line data/tracking.db "SELECT a.id, a.company, a.role, a.location, a.source, a.url, a.posting_captured_at, (SELECT detail FROM events e WHERE e.application_id = a.id AND e.kind = 'note' AND e.source = 'evaluator' ORDER BY e.id DESC LIMIT 1) AS why, a.posting_text FROM applications a WHERE a.id = <id>"
   ```
2. **Show the lead:** a short header, then the **full posting text exactly as stored**. Don't summarise, shorten or rewrite it.
   ```
   Lead 3 of 82 - indeed, found 2026-10-17
   Hooli - Machine Learning Engineer (m/w/d) - München
   https://de.indeed.com/viewjob?jk=...
   Why kept: agentic platform team, matches Agentic/RL focus

   <posting_text>
   ```
   If there is no posting text, say "No posting text stored. See the link." instead.
3. **Ask** with AskUserQuestion, one question:
   - question: `<company> - <role>: apply?`, header `Lead <n>/<total>`
   - options, in this order:
     - `Yes, apply`: "Mark as application outstanding"
     - `No`: "Dismiss. For a reason, choose Other and type e.g. 'no, consulting'."
     - `Skip for now`: "Leave it as a lead"
     - `Stop reviewing`: "End here; the rest stay leads"
4. **Apply the answer:**
   - **Yes, apply:** `UPDATE applications SET status = 'to_apply' WHERE id = ?`
   - **No:** `UPDATE applications SET status = 'dismissed' WHERE id = ?`, with no follow-up question.
   - **Skip for now:** no write.
   - **Stop reviewing:** no write, go to step 3.
   - **Free text through "Other"** (for example "no, consulting firm" or "yes but only if remote"): read it as yes, no or skip, and use the rest as the reason. This is how the user gives reasons.
   - **Reason:** a reason from "Other", or a note added on a choice, is recorded, even on yes or skip:
     `INSERT INTO events (application_id, kind, detail, source) VALUES (?, 'note', ?, 'review')`
   - Never ask for a reason, and never invent one.
5. Go straight to the next lead, with no extra confirmation in between.

## 3. Finish

```
Reviewed 14 of 82: 3 to apply, 9 dismissed, 2 skipped. 68 still open.
To apply: Hooli - ML Engineer; Globex - RL Engineer; ...
```

Dismissed jobs are never suggested again by `/find-jobs`, and the reasons help the evaluator learn the user's taste. Skipped and unreviewed leads appear again next time.
