---
name: echo-watch
description: Monitor the shipped PR's CI and review comments (post-ship watch) and record a proof artifact. Use after shipping, for the active item.
---

# echo watch (Codex)

Codex port of echo's `/echo:watch` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) from what the user
typed if relevant; never fabricate a ticket.

## Steps
1. Find the active ticket:
   ```
   python3 bin/echo-stage status
   ```
   Read the `Active:` line for the ticket id (`[A-Z]+-[0-9]+`). If there is no active item,
   tell the user and stop. Run the watch for the currently-active / just-shipped ticket only.
2. Run the watch (fails open on no `gh`/auth/remote/PR; always writes an artifact):
   ```
   python3 bin/echo-watch run --ticket <active-ticket>
   ```
   This writes `.echo/verify/<ticket>-ci.md` (CI result, PR url, review comments) and prints
   zero or more lines of the form `post <event-key>\t<summary>`.
3. Posting each `post <event-key>` line as a Jira comment uses the Atlassian MCP tools; that
   is Claude-only and is skipped under Codex.
4. Tell the user the artifact location (`.echo/verify/<ticket>-ci.md`) and the CI result. If
   CI failed or there are new review comments, summarize them. If it recorded `skipped`, say
   why (no `gh`/PR yet) and that the watch can be re-run after the PR exists.

## Under Codex
Gates are advisory and orchestration is prose-driven. See `.agents/skills/README.md` for the
Known limitations before relying on this.
