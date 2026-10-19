## 1. Backend

- [x] 1.1 `uv add fastapi uvicorn` and `uv add --dev httpx2` (Starlette's test client deprecates httpx); verify `uv run python -c "import fastapi, uvicorn"` succeeds
- [x] 1.2 Write `tracking/api.py` with `create_app(db_path, prefs_path)` and the read endpoints (`GET /api/applications`, `GET /api/applications/{id}` with evaluator reason, `GET /api/review` with lead ids and `[review].reasons`); verify with unittests on a temp DB: list fields, detail incl. latest evaluator reason, 404, lead order, reasons from a temp TOML, and empty reasons when the file or section is missing
- [x] 1.3 Add `POST /api/review` (validation, `BEGIN IMMEDIATE`, per-row `status='lead'` guard, `review` notes, rollback on error, 503 on lock timeout) as in design.md; verify with unittests: mixed batch (apply + reason / dismiss + reason / dismiss), skip rejected with 422, conflict for a lead changed beforehand (no note, others applied), duplicate ids → 422, invalid decision → 422, non-JSON body → rejected and DB unchanged, and a locked DB → 503 with nothing written
- [x] 1.4 Add `TrustedHostMiddleware`, static serving of `web/dist` with the `index.html` catch-all, the "run pnpm build" fallback, and the `python -m tracking.api` entry on `127.0.0.1:8765`; verify with unittests that a foreign `Host` header is rejected and `/review` returns `index.html` from a temp dist dir, and that `uv run python -m unittest discover tests` passes

## 2. Frontend setup

- [x] 2.1 Scaffold `web/` with Vite React-TS (pnpm), add Mantine core + hooks, TanStack Query, react-router, react-markdown, remark-gfm, vitest; pin a React version all of them support; add the `/api` dev proxy; `web/.gitignore` (from the template) keeps `node_modules` and `dist` out; verify `pnpm --dir web build` succeeds and `git status` shows no `node_modules` or `dist`
- [x] 2.2 Write `src/api.ts` (typed fetchers for the four endpoints) and `src/main.tsx` (providers, routes `/`, `/app/:id`, `/review`, nav between Applications and Review); verify `pnpm --dir web build` type-checks

## 3. Viewing

- [x] 3.1 `StatusBadge.tsx` (one colour per status) and `pages/Applications.tsx` (table: status, role, company, URL link in a new tab; status filter; row click → detail); verify in the running app that all applications are listed, the filter narrows them, and a row without URL still opens
- [x] 3.2 `components/LeadDetail.tsx` (header fields + evaluator reason, markdown body, "no posting text" fallback) and `pages/Detail.tsx`; verify in the running app with the network off that a posting shows formatted headings, bold text and lists, and that one without text points to the URL

## 4. Review

- [x] 4.1 Write `src/review.ts` (`currentLead`, `decide`, `undo`, `toBatch`, `combineReason`, safe localStorage load/save); verify with vitest: current lead skips decided ids, undo pops back to the right lead, plain skips are left out of the batch, the reason joins ticked boxes in list order with the free text, and an empty reason is null
- [x] 4.2 Write `pages/Review.tsx` (LeadDetail, "Lead n of N", reason checkboxes + free text, Y/N/S/U buttons with `Kbd` and `useHotkeys`, prefetch of the next lead, `beforeunload` warning, "no leads" state); verify in the running app that keys decide and advance, typing "n" in the text field doesn't dismiss, U restores the lead and its reason, and a reload keeps the position
- [x] 4.3 Add the apply flow (pending counter, summary with counts and to-apply list, POST, result with conflicts, clear pending + refetch, error keeps pending); verify in the running app on a copy of the DB that a mixed batch gives the expected statuses and one `review` note per reason (`sqlite3` query), and that a lead changed with `tracking.db sql` before applying is listed as a conflict

## 5. Preferences and docs

- [x] 5.1 Propose a `[review].reasons` list to the user, built from the existing `source='review'` notes; after their approval, add it to `data/preferences.toml`; verify it loads with `tomllib` and shows up as checkboxes in the review
- [x] 5.2 Update CLAUDE.md (Current state: `web/`, `tracking/api.py`; how to build and start the UI; `[review].reasons`); verify the commands in it work as written from a clean `web/dist`
