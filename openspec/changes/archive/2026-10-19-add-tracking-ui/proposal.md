## Why

Today the tracking DB can only be seen through `sqlite3` or by asking Claude. Lead review runs through the `review-leads` skill, although no step of it needs judgment: it is a query, a verbatim print, four buttons and two fixed SQL statements. With 70 open leads of about 5k characters each, that review is slow and spends a lot of context. A local web UI makes both viewing and reviewing direct. It is also the base for moving more of the workflow out of Claude later.

## What Changes

- **Local web app**: Vite + React + TypeScript frontend in `web/`, FastAPI backend in `tracking/api.py`. Started with one command, bound to `127.0.0.1` only, and serving the built frontend.
- **Applications table** (read-only): every application with a colour-coded status, role, company and a link to the posting URL, filterable by status. Clicking a row opens the detail view.
- **Detail view** (read-only): company, role, location, source, found date, URL and the evaluator's reason at the top, then the posting text rendered as markdown. Rendering is bundled, so it works offline.
- **Lead review page**: open leads one at a time, with the same detail layout and the decisions apply / dismiss / skip / undo, as buttons and as keys Y / N / S / U.
  - Optional reasons: checkboxes from a list in the preferences file, plus free text. They are combined into one `review` note.
  - Decisions are kept in the browser (they survive a reload) and applied together in one short transaction. The user sees a summary before applying.
  - A lead whose status changed in the meantime (for example by the inbox check) is not overwritten. It is reported as a conflict.
- **Preferences file**: new optional `[review].reasons` list, the reason checkboxes. Seeded once from the user's existing review reasons.

Non-goals:

- Editing applications in the UI (statuses, notes, fields) beyond the lead review.
- Showing the events timeline.
- Changing the `review-leads` skill. It stays as an alternative way to review.
- Hosting the UI anywhere but the local machine, or any login.
- Changes to the preference interview: the reasons list is edited by hand.

## Capabilities

### New Capabilities

- `tracking-ui`: The local web UI: applications table, detail view, and the batched lead review with reason checkboxes.

### Modified Capabilities

- `preferences`: the preferences file gains an optional review part, the list of reason checkboxes.

## Impact

- New: `web/` (Vite app, `package.json`, `pnpm-lock.yaml`), `tracking/api.py`, tests for the API.
- New Python dependencies: `fastapi`, `uvicorn`. Dev: `httpx2` for FastAPI's test client.
- New JS dependencies: React, react-router, TanStack Query, Mantine, react-markdown, remark-gfm. Node and pnpm are needed to build the frontend.
- `web/.gitignore` (from the Vite template) keeps `node_modules/` and `dist/` out of git.
- `data/preferences.toml`: `[review].reasons` added (personal data, not committed).
- CLAUDE.md: how to build and start the UI.
- Writes to `data/tracking.db` from one more writer, through `tracking.db.connect()` like the others.
