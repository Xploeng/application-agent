## 1. Server config

- [x] 1.1 Pull `stickerdaniel/linkedin-mcp-server:4.26.2@sha256:c7aa139c...4b0da6`; verify `docker image inspect` shows the matching repo digest
- [x] 1.2 Add `.mcp.json` with the Docker entry from design.md (`${HOME}` mount, tag@digest); verify it is valid JSON and `claude mcp list` (run in the repo) shows `linkedin`
- [x] 1.3 Add `.claude/settings.json` with the allow/deny lists from design.md; verify valid JSON and that every one of the 19 tools exposed by the pinned image is in exactly one list

## 2. Login (user, interactive)

- [x] 2.1 User runs the login command from design.md and signs in via http://127.0.0.1:6080; verify `~/.linkedin-mcp/profile/` exists and nothing under the repo changed (`git status`)

## 3. Posting capture

- [x] 3.1 Add the LinkedIn capture section to `.claude/skills/update-tracking/SKILL.md` (ID extraction, `get_job_details`, canonical URL, dedupe/fill-in, failure → ask); verify the skill text covers each scenario in `specs/tracking-updates/spec.md`

## 4. End-to-end (new session, needs the login)

- [x] 4.1 In a new session, approve the project MCP server, run a LinkedIn job search and read one job's details; verify both run without a permission prompt
- [x] 4.2 Ask Claude to call `send_message`; verify it is denied
- [x] 4.3 Save one LinkedIn job via update-tracking; verify the new row has source `linkedin`, the canonical URL, non-empty `posting_text` and `posting_captured_at`, and saving it again creates no duplicate

## 5. Documentation

- [x] 5.1 Update CLAUDE.md: LinkedIn MCP (Docker, pinned digest, login/re-login command, upgrade steps, one session at a time, read-only tool policy); verify the commands listed match design.md
