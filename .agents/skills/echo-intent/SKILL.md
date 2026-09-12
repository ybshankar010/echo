---
name: echo-intent
description: Start or refine a work item's intent.md, the Plan-stage artifact. Use when beginning a new echo work item from a ticket and a short goal.
---

# echo intent (Codex)

Codex port of echo's `/echo:intent` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any goal text
from what the user typed; never fabricate a ticket.

## Steps
1. Extract a Jira ticket id (`[A-Z]+-[0-9]+`) from what the user typed. If none is present,
   STOP and ask for it; never fabricate one (organization policy).
2. Initialize the work item:
   ```
   python3 bin/echo-stage init --ticket <TICKET> --title "<short title>"
   ```
3. Load the `echo:intent-template` skill and interview the user briefly if anything is
   unclear (problem, outcome, affected systems, constraints, open questions). Do not invent
   facts. If prior research exists for this ticket at `.echo/artifacts/<ticket>/research.md`
   (or the user points at a `.echo/research/<slug>.md`), read it first and ground the intent
   in its findings, citing them. Fail open: if there is no research doc, just proceed.
4. Write the result to `.echo/artifacts/<ticket>/intent.md` (the `Artifacts:` line from
   `echo-stage status` shows the exact folder). Then record it:
   ```
   python3 bin/echo-stage set-artifact --stage intent
   ```
5. Tell the user to review it and approve when it looks right, then advance with echo-next.

## Under Codex
Gates are advisory and orchestration is prose-driven. See `.agents/skills/README.md` for the
Known limitations before relying on this.
