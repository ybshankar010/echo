---
name: echo-ship
description: Ship the active work item by branch, commit, rebase, push, and open PR, with the ticket id enforced. Use when verification is green and the change is ready to ship.
---

# echo ship (Codex)

Codex port of echo's `/echo:ship` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`), the commit message
(`-m`), and any PR title/desc from what the user typed; never fabricate a ticket.

## Steps
1. Verify there is a fresh passing verification for the active item (check
   `.echo/verify/<ticket>.md` or run the echo-verify flow). If not green, tell the user and
   stop; do not ship unverified work.
2. Show what will happen first with a dry run:
   ```
   python3 bin/echo-git ship -m "<message>" [--title "<PR title>"] [--desc <slug>] --dry-run
   ```
   Present the planned branch, commit, rebase base, and PR title/body.
3. On the user's confirmation, run it for real (drop `--dry-run`). The command enforces the
   Jira ticket id, adds the Co-Authored-By trailer, rebases onto the base branch, and opens
   the PR via `gh`.
4. If a rebase conflict occurs, the command pauses and lists the conflicts; show the user the
   conflicts and stop. Do not auto-resolve.
5. Run the mandatory post-ship watch so CI and review comments are monitored (and so the
   `ship -> done` advance is not blocked by the watch gate). This fails open and always
   writes `.echo/verify/<ticket>-ci.md`:
   ```
   python3 bin/echo-watch run --ticket <active-ticket>
   ```
   Surface its result (CI pass/fail/pending/skipped and any review comments).
6. Give the user the PR link and remind them to approve ship and advance to close the loop.

Posting the PR link to Jira (and the CI/review alerts from the watch) uses the Atlassian MCP
tools; that is Claude-only and is skipped under Codex.

## Under Codex
Gates are advisory and orchestration is prose-driven. See `.agents/skills/README.md` for the
Known limitations before relying on this.
