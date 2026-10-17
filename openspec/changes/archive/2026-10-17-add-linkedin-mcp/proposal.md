## Why

Searching openings and saving postings is manual today. LinkedIn is the main job source, and its postings disappear after a while, which is why the tracking store has a `posting_text` field that is currently empty. Connecting a LinkedIn MCP server lets Claude search and read jobs, and capture the posting text when an application is added.

## What Changes

- Add a project-level `.mcp.json` (committed) that runs [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server) in **Docker**, pinned by **image digest** (`4.26.2`):
  - Isolation: the server and its browser see only the mounted session folder `~/.linkedin-mcp`, outside the repo. It cannot read the user's files or local browser cookies.
  - Upgrades are a deliberate one-line change.
- Allow only read-only job and company tools in the project's `.claude/settings.json`: `search_jobs`, `get_job_details`, `get_company_profile`, `search_companies`, `get_saved_jobs`, `get_my_profile`. Deny every tool that acts as the user or reads private data (messages, connection requests, inbox, feed, people search).
- Log in to LinkedIn once through the container's local login viewer. The session persists in `~/.linkedin-mcp`.
- Extend the `update-tracking` skill so that a LinkedIn job URL or ID is read via `get_job_details`. The application is then added with its full posting text and capture time.

Non-goals:

- The Claude Code plugin install: it is user-scoped, unpinned, and runs without isolation.
- Messaging, networking, or reading the user's LinkedIn inbox.
- Automated or scheduled LinkedIn searches.

Risk accepted by the user: LinkedIn's terms prohibit automated access, and accounts can be restricted. Mitigations are sparing use, a read-only tool set, and one session.

## Capabilities

### New Capabilities

- `linkedin-access`: Read-only LinkedIn job and company access for Claude, isolated and version-pinned, with a persistent login kept outside the repository.

### Modified Capabilities

- `tracking-updates`: adding an application from a LinkedIn job captures its posting text automatically.

## Impact

- New `.mcp.json` and `.claude/settings.json` (both committed).
- `.claude/skills/update-tracking/SKILL.md`: a LinkedIn capture section.
- The user needs Docker Desktop running during sessions that use LinkedIn, and a one-time login.
- No Python code and no new dependencies.
