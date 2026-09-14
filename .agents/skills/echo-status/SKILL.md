---
name: echo-status
description: Show where the active echo work item is, its stage, gates, and the next action. Use when the user asks where the loop stands or what to run next.
---

# echo status (Codex)

Codex port of echo's `/echo:status` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) from what the user
typed if relevant; never fabricate a ticket.

## Steps
1. Run the echo status command:
   ```
   python3 bin/echo-stage status
   ```
2. Also show the plan's "Order of work" checklist and its done/total count (fails open to
   `checklist: none` when there is no active item, plan, or checkboxes):
   ```
   python3 bin/echo-stage checklist
   ```
3. In one or two lines, tell the user the active ticket, its current stage and gate, the
   checklist progress, and exactly what to run next.

## Under Codex
Gates are advisory and orchestration is prose-driven. See `.agents/skills/README.md` for the
Known limitations before relying on this.
