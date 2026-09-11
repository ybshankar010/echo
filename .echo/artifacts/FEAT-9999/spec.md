# Spec: Post Jira comments as /echo:flow progresses

- **Ticket:** FEAT-9999
- **Stage:** Design
- **Derived from:** intent.md (approved)
- **Status:** draft (awaiting `/echo:approve`)

## Overview
Make `/echo:flow` and `/echo:ship` post concise progress comments to the work item's Jira
ticket. Each completed stage gets one comment summarizing what that phase did (a one-line
headline plus a brief statement), gate stops note "awaiting review", and ship posts the PR
link. The actual post is a model-driven call to the Atlassian MCP tool from the command layer;
a small deterministic gate in `bin/echo-stage` decides whether a comment is due and records
that it was posted, so nothing is duplicated and `bin/` stays stdlib-only. Everything fails
open: no ticket, no MCP, or a post error means the loop runs unchanged and posts nothing.

## Requirements
1. When `/echo:flow` completes a stage (intent, spec, plan, build, test), it posts exactly one
   Jira comment for that stage: a one-line headline plus a brief statement of what the phase
   produced or decided, derived from that stage's artifact or check result.
2. The per-stage comment is posted once whether the stage auto-advances or the flow stops at
   that stage's gate. On a gate stop the statement notes the stage is awaiting review.
3. `/echo:ship` posts one comment containing the opened PR link, after the PR is created.
4. A comment is posted only when the active item has a valid ticket id (`[A-Z]+-[0-9]+`).
   Ticketless work (topic-first `/echo:research`) posts nothing.
5. No comment is posted more than once for the same (ticket, event). Re-running `/echo:flow`
   or resuming after a gate does not duplicate a comment.
6. No comment is posted for internal maker-checker iterations; only at stage completion, gate
   stop, and ship.
7. Fail open: if the Atlassian MCP is unavailable or a post errors, the loop and ship continue
   unaffected and post nothing. A Jira failure never blocks a stage or a ship.
8. echo never changes the Jira workflow status field. Comments only.
9. echo never fabricates a ticket id to comment.
10. The post uses the Atlassian MCP tool `addCommentToJiraIssue`. No network code lives in
    `bin/` or `lib/` (they stay standard-library only).

## Design
- **Deterministic gate (`bin/echo-stage`, stdlib).** Two subcommands backed by a committed,
  per-ticket ledger of posted events (mirrors the `verify/` and `review/` artifact pattern):
  - `comment-needed --event <event>`: prints `post <ticket>` when the active item has a valid
    ticket and `<event>` is not yet in the ledger; prints `skip` otherwise (no ticket, or
    already posted, or no active item). Always exits 0 (fail open).
  - `comment-done --event <event>`: records `<event>` for the active ticket in the ledger.
  Reuses `ec.active_item`, `ec.load_state`, `ec.TICKET_RE`. Ledger storage (a small JSON file
  under `.echo/` keyed by ticket, or a field on the state item) is a plan-stage choice.
  Events: `stage:intent`, `stage:spec`, `stage:plan`, `stage:build`, `stage:test`, `ship`.
- **`commands/flow.md`.** After each stage's work is complete (at the point flow auto-advances
  it, or when flow stops at that stage's gate), call `comment-needed --event stage:<stage>`.
  If `post`, build the comment from that stage's artifact/check result and call
  `addCommentToJiraIssue` for the resolved ticket, then `comment-done --event stage:<stage>`.
  Wrap the MCP call so any error is swallowed and the loop continues.
- **`commands/ship.md`.** After the PR is opened, call `comment-needed --event ship`; if `post`,
  comment with the PR URL, then `comment-done --event ship`.
- **Resolving the Jira target.** The command resolves the Atlassian `cloudId` via
  `getAccessibleAtlassianResources` and uses the work item's ticket key as `issueIdOrKey`. If
  the cloudId cannot be resolved, treat it as fail open (skip).
- **Comment templates** (headline + brief statement; statement grounded in the real artifact,
  never fabricated):
  - intent: "echo: intent captured." + the problem/outcome in one sentence.
  - spec:   "echo: spec drafted." + the key requirements or decisions.
  - plan:   "echo: plan ready for review." + the approach / files that change.
  - build:  "echo: build complete, review clean." + what changed.
  - test:   "echo: verified green." + the checks that ran.
  - ship:   "echo: shipped." + the PR URL.
  A gate-stop variant appends "awaiting your review".

## Flagged concerns
- **Testability.** The MCP post cannot run in CI (no network or MCP there). Mitigation: unit-test
  the deterministic gate (`comment-needed` / `comment-done`, dedup, ticketless skip, fail open);
  verify the real post manually with the Atlassian MCP connected. Acceptance is split accordingly.
- **Data leakage into Jira.** Comments are derived from design artifacts. Keep them to the
  headline plus a brief phase summary; never paste diffs, file contents, secrets, or tokens.
  The templates constrain content to enforce this.
- **Multi-site Atlassian / wrong cloudId.** `addCommentToJiraIssue` needs the correct cloudId.
  Resolve via `getAccessibleAtlassianResources`; if ambiguous or none, fail open (skip).
- **MCP flakiness.** Some MCP servers were unreliable this session. Any MCP error is treated as
  skip, never a loop failure (Requirement 7).

## Non-goals
- No Jira workflow status transitions (comments only).
- No wiring of the standalone `/echo:approve` (a later option).
- No comments for ticketless or research-only work.
- No config toggle; commenting is always on when a ticket and the MCP are present.
- No editing, threading, or backfilling of comments for stages already passed.

## Acceptance criteria
Deterministic (unit-testable, no MCP):
- `comment-needed --event stage:spec` prints `post FEAT-9999` on a fresh ticketed item, and
  `skip` after `comment-done --event stage:spec` records it.
- `comment-needed` prints `skip` when the active item has no valid ticket (ticketless research).
- The ledger is per ticket: an event recorded for one ticket does not suppress it for another.
- `comment-needed` exits 0 and prints `skip` when there is no active item (fail open).
Manual (Atlassian MCP connected):
- `/echo:flow <TICKET> <goal>` posts one comment per completed stage and one at the plan gate
  stop; a re-run posts no duplicates.
- `/echo:ship` posts one comment containing the real PR URL.
- With the MCP disconnected, the loop and ship run normally and post nothing, with no error.
- The Jira workflow status field is unchanged throughout.
