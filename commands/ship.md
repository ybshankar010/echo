---
description: Ship the active work item — branch, commit, rebase, push, open PR (ticket enforced)
argument-hint: -m "commit message" [--title "PR title"] [--desc slug] [--dry-run]
---

Run the Ship stage for the active echo work item: $ARGUMENTS

Write the `-m` descriptive prose in Simplified Technical English (load `echo:ste-writing`).
Keep the `TICKET: ` prefix, the `Ticket: <id>` body line, and the Co-Authored-By trailer
exactly as policy requires; STE guides only the prose around them.

1. Verify there is a fresh passing verification for the active item (check
   `.echo/verify/<ticket>.md` or run `/echo:verify`). If not green, tell me and stop —
   do not ship unverified work.
2. Show me what will happen first with a dry run:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-git" ship $ARGUMENTS --dry-run
   ```
   Present the planned branch, commit, rebase base, and PR title/body.
3. On my confirmation, run it for real (drop `--dry-run`). The command enforces the
   Jira ticket id, adds the Co-Authored-By trailer, rebases onto the base branch, and
   opens the PR via `gh`.
4. If a rebase conflict occurs, the command pauses and lists the conflicts — show me
   the conflicts and stop. Do not auto-resolve.
5. On success, post the PR link to Jira as a progress comment (best-effort, fail open):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" comment-needed --event ship
   ```
   - If it prints `skip` (no ticket, no active item, or already posted) -> post nothing.
   - If it prints `post <ticket>` -> resolve the Atlassian `cloudId` via
     `getAccessibleAtlassianResources` (if it cannot be resolved, treat as skip and post
     nothing), then call `addCommentToJiraIssue` with that `cloudId` and the ticket key as
     `issueIdOrKey`, using the template "echo: shipped." + the opened PR URL. Never change the
     Jira status field. If the MCP call errors, swallow it and continue. Only after a successful
     post, record it:
     ```
     python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" comment-done --event ship
     ```
6. Run the mandatory post-ship watch so CI and review comments are monitored (and so the
   `ship -> done` advance is not blocked by the watch gate). This fails open and always writes
   `.echo/verify/<ticket>-ci.md`:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-watch" run --ticket <active-ticket>
   ```
   Surface its result to me (CI pass/fail/pending/skipped and any review comments). For each
   `post <event-key>\t<summary>` line it prints, post the Jira comment and record it exactly as
   `/echo:watch` step 3 does (best-effort, fail open; never change Jira status).
7. Give me the PR link and remind me to `/echo:approve` ship + `/echo:next` to close the loop.
