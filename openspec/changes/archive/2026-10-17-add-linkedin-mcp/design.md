## Context

The upstream server, stickerdaniel/linkedin-mcp-server, drives a patched Chromium (Patchright) with the user's LinkedIn session and exposes 19 tools over stdio in the pinned `4.26.2`. `get_job_apply_url` only arrives in `4.27.0`; it is left out until an upgrade. It ships as a Claude Code plugin, a uvx package, and a Docker image. Docker 27.5 is installed. The repo has no `.mcp.json` or project `.claude/settings.json` yet. See proposal.md for motivation and specs/ for behaviour.

## Goals / Non-Goals

**Goals:**

- Isolate the server, pin its version, and keep everything as committed config, with zero code.

**Non-Goals:**

- No wrapper skill for LinkedIn search. Claude calls the tools directly, and only posting capture is wired into `update-tracking`.

## Decisions

### Docker via project `.mcp.json`

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "${HOME}/.linkedin-mcp:/home/pwuser/.linkedin-mcp",
        "stickerdaniel/linkedin-mcp-server:4.26.2@sha256:c7aa139cfaaecc8ae9f5e810d6517e5e36b5a1a52cadcb4eef6f0832810b4da6"
      ]
    }
  }
}
```

- **`${HOME}`:** Claude Code expands environment variables in `.mcp.json`, so the mount path works without hard-coding the user's home directory. The README warns that `~` itself is not expanded.
- **`tag@digest`:** the tag documents the version, and Docker resolves the image by digest, so a moved tag can't change what runs. `4.26.2` is two weeks old with no patch since. `4.27.0`, released a week ago, was skipped for now.
- **What the container sees:** only `~/.linkedin-mcp`, which holds the profile, cookies and session. It has no host network ports in stdio mode and no access to local browsers, so the uvx variant's auto-import of Chrome cookies can't happen.

Alternatives considered:

- The plugin: installed per user, always the latest release, not isolated.
- `.mcp.json` + uvx: not isolated, and auto-imports cookies from the local browser by default.

### Tool permissions in `.claude/settings.json`

Claude Code names MCP tools `mcp__<server>__<tool>`. Deny rules take precedence over allow rules, so the deny list names each tool explicitly; a blanket `mcp__linkedin` deny would also block the allowed tools.

```json
{
  "permissions": {
    "allow": [
      "mcp__linkedin__search_jobs", "mcp__linkedin__get_job_details",
      "mcp__linkedin__get_company_profile",
      "mcp__linkedin__search_companies", "mcp__linkedin__get_saved_jobs",
      "mcp__linkedin__get_my_profile"
    ],
    "deny": [
      "mcp__linkedin__send_message", "mcp__linkedin__connect_with_person",
      "mcp__linkedin__get_inbox", "mcp__linkedin__get_conversation",
      "mcp__linkedin__search_conversations", "mcp__linkedin__get_person_profile",
      "mcp__linkedin__get_sidebar_profiles", "mcp__linkedin__search_people",
      "mcp__linkedin__get_company_employees", "mcp__linkedin__get_company_posts",
      "mcp__linkedin__get_feed", "mcp__linkedin__search_posts",
      "mcp__linkedin__close_session"
    ]
  }
}
```

A tool added by a future version would be neither allowed nor denied, so Claude Code would ask before running it. Re-check this list when upgrading the pin.

### One-time login

```
docker run -it --rm -v ~/.linkedin-mcp:/home/pwuser/.linkedin-mcp \
  -p 127.0.0.1:6080:6080 <same image@digest> --login --login-viewer
```

Run this, open http://127.0.0.1:6080, sign in (completing any captcha or app confirmation), then stop the container. The viewer port is bound to localhost only and exists only during login. To log in again after LinkedIn expires the session, run the same command.

### LinkedIn capture in `update-tracking`

Add a short section to `.claude/skills/update-tracking/SKILL.md`:

1. Take the job ID from `linkedin.com/jobs/view/<id>` or a search result.
2. Call `get_job_details`.
3. Check whether an application with that URL already exists:
   - **Yes, with empty `posting_text`:** fill it in.
   - **Yes, with text already:** report that it is already tracked.
   - **No:** insert company, role, location, `url = https://www.linkedin.com/jobs/view/<id>/`, `source = 'linkedin'`, `status = 'lead'` (unless stated otherwise), `posting_text`, and `posting_captured_at`.
4. If the tool fails, say so and ask before inserting without the posting text.

The URL is normalised to that canonical form, so the unique `url` column catches duplicates from tracking parameters such as `?refId=...`.

## Risks / Trade-offs

- [LinkedIn restricts the account] → The user accepted this risk. Mitigations: read-only tools, use on request only (no loops or schedules), one persistent session from one IP.
- [Two Claude sessions start two containers on the same profile] → Use LinkedIn from one session at a time. This is documented in CLAUDE.md, not enforced.
- [Docker Desktop not running] → The MCP server fails to start, and the LinkedIn tools are missing in that session. Everything else in the repo still works.
- [Pinned image ages, and LinkedIn layout changes break scraping] → Upgrade by editing the tag and digest in `.mcp.json`, then re-check the tool list in `settings.json`.
- [Container start adds latency to sessions] → The server starts at session start, and the image is pulled once.

## Migration Plan

1. `docker pull` the pinned image.
2. Run the login.
3. Commit `.mcp.json`, `settings.json` and the skill edit.
4. In a new session, approve the project MCP server when Claude Code asks.

Rollback: delete `.mcp.json` and the permission entries. `~/.linkedin-mcp` can be removed to drop the session.
