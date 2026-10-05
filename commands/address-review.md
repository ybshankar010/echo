---
description: Address open PR review threads on the active item - analyse, fix via builder, verify, push, resolve threads
argument-hint: [-- <focus or extra instruction>]
---

Address the open review threads on the current PR for the active echo work item. This
operates on the currently checked-out PR branch: read the open threads, analyse the full
code and the Jira ticket, agree the changes in Jira, have the `builder` subagent make the
edits, verify, push a follow-up commit to the existing PR branch, and resolve each
addressed thread. Never opens a second PR and never self-approves a gate. Extra focus:
$ARGUMENTS

Load the `echo:address-review` skill (the reusable methodology and safety rules) before you
start, the way `/echo:plan` loads `echo:plan-template`.

Write the `-m` descriptive prose and the Jira comment prose in Simplified Technical English
(load `echo:ste-writing`). Keep the `TICKET: ` prefix, the `Ticket: <id>` line, and the
Co-Authored-By trailer exactly as policy requires; STE guides only the prose around them.

1. Derive the ticket from the checked-out branch and confirm the gate is open:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status
   ```
   Read the branch ticket (`[A-Z]+-[0-9]+`, the same value `ec.ticket_from_branch()`
   returns). If a `--ticket` was passed and it does not match the branch's ticket, STOP and
   tell me: a followup must act on the branch's own PR, never a different ticket's. Then
   confirm that ticket is the echo active item on the `Active:` line. If it is not the active
   item, STOP and tell me to check out the PR branch (so the active item matches) or set
   `plan_guard_override=true` in `.echo/config.json` - otherwise the plan-guard hook would
   block the builder's edits mid-run (exit 2). Do not force anything.
2. Fetch the open review threads (fails open: no `gh`/auth/remote/PR prints nothing):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-review-comments" fetch
   ```
   Each printed line is `thread\t<id>\t<path>:<line>\t<author>\t<one-line body>`. It also
   writes `.echo/review/<ticket>-comments.md`. If it prints no thread lines, there is nothing
   unresolved: tell me and stop cleanly.
3. Analyse before changing anything. Read the Jira ticket for intent (under Claude Code:
   resolve the Atlassian `cloudId` via `getAccessibleAtlassianResources`, then `getJiraIssue`
   with that `cloudId` and the ticket key; under Codex there is no Atlassian MCP, so skip
   this). For each thread, read the complete code around it (`git diff` and the referenced
   files), not just the one-line body, so you understand what the reviewer is asking for.
4. Post the agreed changes to Jira (best-effort, fail open; never change the status field):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" comment-needed --event address-review:<head-sha>
   ```
   Use the PR head sha (from `echo-review-comments` / `git rev-parse HEAD`) in the event key
   so a new round of review re-alerts. If it prints `skip`, post nothing. If it prints
   `post <ticket>`, resolve the `cloudId` via `getAccessibleAtlassianResources` (if it cannot
   be resolved, treat as skip), call `addCommentToJiraIssue` with that `cloudId` and the
   ticket key, stating the changes you agreed to make (prose only - never paste diffs, file
   contents, secrets, or tokens). Only after a successful post:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" comment-done --event address-review:<head-sha>
   ```
5. Spawn the `builder` subagent (Task tool) with the thread list as its fix scope: "Address
   these PR review threads on the active item by editing the referenced code. Reuse existing
   patterns. Fix the code, not the tests - never weaken or delete a test to go green. Do NOT
   commit, branch, or push. For each thread you address, run `python3
   \"${CLAUDE_PLUGIN_ROOT}/bin/echo-review-comments\" mark --thread <id> --status addressed`.
   Report per thread whether you addressed it or deferred it and why." Pass along $ARGUMENTS.
   The builder edits only; committing and pushing happen in steps 6-7.
6. Verify (proof); stop if red:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-verify"
   ```
   If verification fails, STOP and show me - do not push unverified work.
7. Push a follow-up commit to the existing PR branch. Show the dry run first, then run it for
   real on my confirmation (like `/echo:ship`). The CLI prepends the ticket id and the
   Co-Authored-By trailer, does not rebase, and never opens a new PR:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-git" followup -m "address review comments" --dry-run
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-git" followup -m "address review comments"
   ```
8. Resolve each addressed thread (only after a green verify and a successful push):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-review-comments" resolve --thread <id>
   ```
   Run it once per thread the builder marked `addressed`. Then summarize for me: which threads
   were addressed, the PR url the followup pushed to, which threads are now resolved, and any
   threads deferred (with the reason). Never resolve a thread you did not actually address, and
   never approve an echo gate for me.
