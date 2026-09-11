# Intent: Post Jira comments as /echo:flow progresses

- **Ticket:** FEAT-9999
- **Stage:** Plan
- **Author:** echo-contributor
- **Status:** draft (awaiting `/echo:approve`)

## Problem
The `/echo:flow` orchestrator moves a work item through intent, spec, plan, build, test,
and ship, and knows exactly when each stage is done, when it pauses for a human gate, and
when it ships. None of that reaches the Jira ticket. Today the developer has to comment on
the ticket by hand to keep it current, which is easy to forget and just repeats status echo
already holds.

## Proposed outcome
As `/echo:flow` runs, the work item's Jira ticket receives one concise comment per stage that
summarizes what that phase did or decided: a one-line headline plus a brief statement. It also
comments at each gate stop that needs review, and posts a ship comment carrying the PR link.
echo posts comments only and never changes the Jira workflow status (the team's Jira process
already tracks that). Commenting is always on when the ticket and the Atlassian MCP are present,
and fails open (posts nothing, loop unaffected) when the MCP is not connected.

## Affected users / systems
- The developer driving echo (less manual Jira upkeep).
- `commands/flow.md` (the orchestrator, primary), and `commands/ship.md` (the PR-link comment
  on ship). Wiring the standalone `/echo:approve` is a later option, out of scope here.
- The Atlassian Jira MCP tool `addCommentToJiraIssue` (available this session). Posting is a
  model-driven action from command prose, not from `bin/` (echo's bin stays stdlib-only, no
  network).

## Constraints
- stdlib-only determinism in `bin/`/`lib/`; the Jira post happens via the MCP tool in the
  command layer, not in a Python CLI. No new config key is needed: comment whenever a ticket
  and the Atlassian MCP are present.
- Comments only. Never transition the Jira workflow status; the team's Jira process owns that.
- Fail open: if the Atlassian MCP is not connected, the loop runs exactly as today and posts
  nothing. A Jira failure never blocks a stage or a ship.
- Comment only when the active item has a valid ticket id (`[A-Z]+-[0-9]+`). Ticketless work,
  such as topic-first `/echo:research` stored under `.echo/research/<slug>.md`, gets no Jira
  comment and that is correct: there is no ticket to annotate. Never fabricate a ticket to
  comment. This changes nothing about echo's existing rule that the build loop requires a ticket.
- One concise comment per stage transition, per gate stop, and at ship. Not per internal
  maker-checker iteration, and do not duplicate a comment already posted for the same event.
- The ticket id is already required and validated (`[A-Z]+-[0-9]+`); comment on that ticket
  only, never a fabricated one. No secrets or tokens; use the connected MCP.
- No em dashes in user-facing strings or docs.

## Open questions
1. Exact comment wording and structure per stage (the one-line headline plus what the brief
   summary pulls from: the stage artifact, the checker result, files changed). Leaning: derive
   the headline from the stage and the summary from that stage's artifact or check result.
   Decide the concrete templates in the spec.

## How we know it worked (leading signals)
- Running `/echo:flow FEAT-1234 <goal>` posts one Jira comment per stage that summarizes that
  phase (one-line headline plus a brief statement), a comment at each gate stop, and a ship
  comment with the PR link. No comment per inner maker-checker iteration.
- The Jira workflow status is unchanged by echo; only comments are added.
- With the Atlassian MCP disconnected, the loop behaves exactly as before and posts nothing.
- Ticketless work (topic-first research, no `[A-Z]+-[0-9]+` id) posts nothing and runs normally.
- The ship comment carries the real PR link that `/echo:ship` opened.
