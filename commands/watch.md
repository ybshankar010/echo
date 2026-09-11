---
description: Monitor the shipped PR's CI and review comments (post-ship watch) and record a proof artifact
argument-hint: (run after /echo:ship, for the active item)
---

Run the post-ship watch for the active echo work item, then post any due Jira alerts.

1. Find the active ticket. Run:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status
   ```
   Read the `Active:` line for the ticket id (`[A-Z]+-[0-9]+`). If there is no active item,
   tell me and stop. The watch must run for the currently-active / just-shipped ticket: the
   `--ticket` you pass and the ledger that `comment-done` writes to are the same active item,
   so never run this against a different ticket than the active one.
2. Run the watch (fails open on no `gh`/auth/remote/PR; always writes an artifact):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-watch" run --ticket <active-ticket>
   ```
   This writes `.echo/verify/<ticket>-ci.md` (CI result, PR url, review comments) and prints
   zero or more lines of the form `post <event-key>\t<summary>`.
3. For each `post <event-key>\t<summary>` line, post one Jira comment (best-effort, fail open):
   resolve the Atlassian `cloudId` via `getAccessibleAtlassianResources` (if it cannot be
   resolved, treat as skip and post nothing), then call `addCommentToJiraIssue` with that
   `cloudId` and the active ticket key as `issueIdOrKey`, using the `<summary>` text as the
   comment ("echo: " + the summary). Never paste diffs, file contents, secrets, or tokens.
   Never change the Jira status field. If the MCP call errors, swallow it and continue. Only
   after a successful post, record it so it never double-posts:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" comment-done --event <event-key>
   ```
4. Tell me the artifact location (`.echo/verify/<ticket>-ci.md`) and the CI result. If CI
   failed or there are new review comments, summarize them so I can act. If it recorded
   `skipped`, say why (no `gh`/PR yet) and that I can re-run `/echo:watch` after the PR exists.
