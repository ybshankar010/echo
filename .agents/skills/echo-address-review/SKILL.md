---
name: echo-address-review
description: Address open PR review threads on the active item - analyse, fix via the builder role, verify, push a follow-up commit, and resolve the threads. Use when a shipped PR has open review threads to act on.
---

# echo address-review (Codex)

Codex port of echo's `/echo:address-review` command. It drives the same loop through the
stdlib `bin/echo-*` CLIs (unchanged). It operates on the currently checked-out PR branch:
read the open review threads, analyse the code, fix via the builder role, verify, push a
follow-up commit to the existing PR branch, and resolve each addressed thread. Never opens a
second PR and never self-approves a gate.

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) from the branch and
any focus text from what the user typed; never fabricate a ticket.

Write the `-m` descriptive prose and any Jira comment prose in Simplified Technical English
(load the `ste-writing` skill). Keep the `TICKET: ` prefix, the `Ticket: <id>` line, and the
Co-Authored-By trailer exactly as policy requires; STE guides only the prose around them.

## Steps
1. Derive the ticket from the checked-out branch and confirm the gate is open (`python3
   bin/echo-stage status`). The branch ticket is what `ec.ticket_from_branch()` returns. If a
   `--ticket` was given and it disagrees with the branch, STOP. Confirm that ticket is the
   echo active item; if not, STOP and tell the user to check out the PR branch or set
   `plan_guard_override=true` in `.echo/config.json`, so the builder's edits are not blocked.
2. Fetch the open review threads (fails open: no `gh`/auth/remote/PR prints nothing):
   `python3 bin/echo-review-comments fetch`. Each line is
   `thread\t<id>\t<path>:<line>\t<author>\t<one-line body>`, and it writes
   `.echo/review/<ticket>-comments.md`. If no thread lines print, stop cleanly.
3. Analyse before changing anything. Read the complete code around each thread (`git diff` and
   the referenced files), not just the one-line body. Under Codex there is no Atlassian MCP,
   so skip the Jira ticket read.
4. Under Codex the Jira MCP is not wired, so skip the agreed-changes Jira comment (post it
   yourself if you want it). Never change the Jira status field.
5. Fix via the `builder` role (`.codex/agents/builder.toml`), delegating in prose with the
   thread list as fix scope: "Address these PR review threads by editing the referenced code.
   Reuse existing patterns. Fix the code, not the tests - never weaken or delete a test. Do
   NOT commit, branch, or push. For each thread you address, run `python3
   bin/echo-review-comments mark --thread <id> --status addressed`. Report per thread whether
   you addressed or deferred it and why."
6. Verify (proof): `python3 bin/echo-verify`. If it fails, STOP - do not push unverified work.
7. Push a follow-up commit to the existing PR branch (show the dry run first, then run for
   real). The CLI prepends the ticket id and the Co-Authored-By trailer, does not rebase, and
   never opens a new PR:
   `python3 bin/echo-git followup -m "address review comments" --dry-run` then without
   `--dry-run`.
8. Resolve each addressed thread only after a green verify and a successful push:
   `python3 bin/echo-review-comments resolve --thread <id>` once per thread marked
   `addressed`. Then summarize: threads addressed, the PR url, threads resolved, and any
   deferred (with reason). Never resolve a thread you did not address, and never approve a
   gate.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`builder` via the Task tool, delegate in prose to `.codex/agents/builder.toml`. See
`.agents/skills/README.md` for the Known limitations before relying on this.
