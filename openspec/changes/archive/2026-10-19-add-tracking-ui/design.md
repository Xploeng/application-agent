## Context

- **Store:** `data/tracking.db` in WAL mode. Writers go through `tracking.db.connect()`, which sets foreign keys and a 5 s busy timeout. A trigger logs status changes to `events` and bumps `updated_at`.
- **Other writers:** `check-inbox`, `find-jobs` (`add_leads.py`) and `update-tracking`. They may run while the UI is open.
- **Review semantics** come from the `lead-review` spec: apply → `to_apply`, dismiss → `dismissed`, skip leaves `lead` (in the UI a skip never has a reason), and reasons are `note` events with `source='review'`.
- **The evaluator digest** reads only the latest `review` note per dismissed application (`jobs/scrape.py`, `ORDER BY e.id DESC LIMIT 1`).
- **Posting text** is JobSpy markdown, about 5k characters on average and 8k at most.
- `jobs.scrape.load_prefs` exits when the file is missing, so the API can't reuse it.
- `.gitignore` already ignores `dist/` and `lib/`. The second matters: no `web/src/lib/` folder, because it would be ignored.

See proposal.md for motivation, and specs/ for behaviour.

## Goals / Non-Goals

**Goals:**

- The UI never holds the write lock longer than one short apply transaction.
- One Python code path writes to the DB (`tracking.db.connect()`). The frontend never touches SQLite.
- Easy to grow: typed API, a router, a component library.

**Non-Goals:**

- No DB schema change.
- No auth, no multi-user setup, no deployment.
- No frontend for the other skills yet.

## Decisions

### Layout

```
tracking/api.py      FastAPI app + `python -m tracking.api` entry (uvicorn, 127.0.0.1:8765)
web/                 Vite + React + TS, pnpm
  src/main.tsx       MantineProvider, QueryClientProvider, router
  src/api.ts         typed fetch helpers
  src/review.ts      pure pending-decision logic (tested with vitest)
  src/pages/         Applications.tsx, Detail.tsx, Review.tsx
  src/components/    LeadDetail.tsx (shared by Detail and Review), StatusBadge.tsx
  vite.config.ts     dev proxy /api -> http://127.0.0.1:8765
```

- **Normal use:** `pnpm --dir web build` once, then `uv run python -m tracking.api` and open http://127.0.0.1:8765.
- **Development:** run uvicorn plus `pnpm --dir web dev`.

### Backend: FastAPI in Python, not a Node server

- It reuses `tracking.db.connect()` and the existing Python tests, so the pragmas and the status rules live in one language.
- Pydantic validates the review batch at the boundary.
- **Alternative considered:** a Node server with better-sqlite3 in the Vite project. That would be one language for the UI, but a second copy of the DB access rules.

`create_app(db_path, prefs_path)` builds the app, so tests can use a temp DB and a temp preferences file. The module-level `app` uses the defaults (`tracking.db.DB_PATH`, `data/preferences.toml`).

### API

| Method + path | Returns |
|---|---|
| `GET /api/applications` | `[{id, company, role, status, url}]`: all rows, no posting text |
| `GET /api/applications/{id}` | all display fields + `posting_text` + `evaluator_reason` (latest `note` with `source='evaluator'`); 404 if missing |
| `GET /api/review` | `{lead_ids: [...], reasons: [...]}`: open leads by `id`, and `[review].reasons` (empty if no file or section) |
| `POST /api/review` | body `{decisions: [{id, decision: "apply"\|"dismiss", reason: str\|null}]}` (skips are never sent) → `{applied: {to_apply: n, dismissed: n, notes: n}, conflicts: [id, ...]}` |

The review page fetches each lead through the detail endpoint. TanStack Query prefetches the next one, so moving on feels instant.

### Applying a batch: one short transaction, guarded per row

```
POST /api/review
  validate: decision is apply or dismiss, ids unique, reason stripped ("" -> null)
  conn = connect(db); BEGIN IMMEDIATE        -- take the write lock up front
  for d in decisions:
    UPDATE applications SET status=? WHERE id=? AND status='lead'
    rowcount == 0 -> conflict, continue (no note)
    if d.reason:   INSERT INTO events (application_id, kind, detail, source)
                   VALUES (?, 'note', ?, 'review')
  COMMIT  (any exception -> ROLLBACK, 5xx/503, client keeps pending)
```

- **Why not hold a transaction open for the whole review:**
  - SQLite has one write lock. Holding it for a 30-minute review makes check-inbox and find-jobs fail with `SQLITE_BUSY` after the 5 s timeout.
  - A closed tab or a killed server would roll back every decision.
  - Python's `sqlite3` doesn't expose SQLite's session extension.
- **Why per-row conflicts, not all-or-nothing on a conflict:** a lead that moved is a normal event, not an error. Rejecting 30 decisions because of one would force a redo. A real failure (lock timeout, I/O) still rolls back everything.
- **A lock timeout** returns 503 with a message, and the decisions stay pending.

### Pending decisions in the browser

- **Storage:** `localStorage["review.pending"]` holds `[{id, decision, reason}]` in decision order. Every read and write is wrapped, so a blocked storage falls back to memory.
- **Skips** are kept as pending too, so undo and the position survive a reload. They never carry a reason (the UI drops anything ticked or typed) and the client leaves them out of the POST. The UI deliberately differs from the review-leads skill here, which allows a reason on skip.
- **Current lead** = the first id in `lead_ids` with no pending decision. Decisions are always made on the current lead, so they follow queue order. That makes undo a simple `pop()`: the popped lead is again the first undecided one.
- **Pending ids missing from `lead_ids`** (changed elsewhere since the last load) stay pending. The server reports them as conflicts on apply.
- **Leaving the page:** a `beforeunload` handler warns while pending is non-empty.
- **After a successful apply:** pending is cleared, the result (counts + conflicts) is shown, and the queries are refetched.
- **Logic location:** all of this lives in `review.ts` as pure functions (`currentLead`, `decide`, `undo`, `toBatch`, `combineReason`), so vitest can test it without a DOM.

**Alternative considered:** writing each decision immediately and undoing with a reverse update. That's simpler server-side and durable at once, but it gives no summary before writing, and undo would add a second pair of `status_change` events.

### Reasons → one note

- `combineReason(ticked, free)` = ticked reasons in list order, then the trimmed free text, joined with `"; "`. Null if nothing is given.
- **Why one note:** the evaluator digest reads one note per application.
- The checkbox and free-text state reset when moving to the next lead. Each pending decision stores its ticked boxes and text separately, so an undo restores them exactly. The note is combined only when the batch is built.

### Keys

- Mantine `useHotkeys` for `y`, `n`, `s`, `u`. By default it ignores key presses in inputs and textareas, which covers the "typing a reason" scenario.
- The buttons show the key as a `Kbd` label.

### Local-only hardening

- uvicorn binds `127.0.0.1` only.
- `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])` rejects DNS-rebinding requests, so a malicious page can't read the store.
- **JSON-only POST:** FastAPI rejects a body model sent with a non-JSON content type. A cross-site form post can't send JSON without a CORS preflight, and no CORS headers are set. A test asserts this rather than trusting the framework.

### Serving the frontend

- `/api/*` routes come first.
- `StaticFiles` serves `web/dist/assets`.
- A catch-all `GET /{path}` returns `web/dist/index.html`, so a reload on `/app/12` or `/review` works with the browser router.
- If `web/dist` is missing, `/` returns a plain message: "run `pnpm --dir web build`".

### Frontend libraries

- **Mantine (core + hooks):** table, badge, checkbox, button, kbd and `useHotkeys`, with no Tailwind setup.
- **TanStack Query:** caching and prefetching.
- **react-router:** client routes.
- **react-markdown + remark-gfm:** markdown rendering, bundled, no network at runtime. Raw HTML in postings is **not** rendered (react-markdown's default), so scraped text can't inject markup.
- **Status colours:** one fixed map in `StatusBadge.tsx`, now in `src/status.ts` (shared with the filter chips): filled badges with `autoContrast`, no near-black `dark` colour, so they read in dark mode.

### Preferences

```toml
[review]
reasons = ["AI-adjacent", "boring use case", "consulting", "DevOps", "too senior"]
```

- The file is read with `tomllib` on each `GET /api/review`, so hand edits show up without a restart.
- It's seeded once during implementation from the existing `source='review'` notes, with the user's approval of the list.

## Risks / Trade-offs

- **Pending decisions live only in that browser's localStorage** → losing them costs only re-review time, and nothing is half-written. The apply button stays visible with its pending count.
- **Two writers decide the same lead** (the UI and the review-leads skill) → the `status='lead'` guard reports the UI's decision as a conflict instead of overwriting.
- **The skill and the UI drift on review semantics** → both follow the `lead-review` rules. The UI spec restates them, and the API tests cover the mapping.
- **Node/pnpm become a requirement for building** → only to build. Running uses the built `web/dist` from Python. `dist/` stays gitignored, so a fresh clone needs one build.
- **Large JS dependency tree** → accepted by the user for future growth. Versions are pinned in `pnpm-lock.yaml`.
- **Mantine/react-markdown support for the latest React** isn't verified yet → pin a React version both support at setup time.

## Migration Plan

- Nothing to migrate in the DB.
- Add `[review].reasons` to `data/preferences.toml`.
- Rollback: delete `web/` and `tracking/api.py`, and remove the dependencies. The skill keeps working.
