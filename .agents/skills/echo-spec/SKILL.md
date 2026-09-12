---
name: echo-spec
description: Generate spec.md (Design stage) from an approved intent.md. Use when the intent gate is approved and a requirements plus design spec is needed.
---

# echo spec (Codex)

Codex port of echo's `/echo:spec` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any goal text
from what the user typed; never fabricate a ticket.

## Steps
1. Confirm the intent gate is approved:
   ```
   python3 bin/echo-stage status
   ```
   If intent is not approved, STOP and tell the user to approve the intent first.
2. Load the `echo:spec-template` skill and read `.echo/artifacts/<ticket>/intent.md`
   (the `Artifacts:` line from `echo-stage status` shows the ticket-scoped folder).
3. Write a full requirements + design spec to `.echo/artifacts/<ticket>/spec.md`, flagging
   any security / compliance / UX concerns. Ground every requirement in the intent; mark
   anything inferred as an assumption.
4. Record it (the path defaults to the ticket-scoped location):
   ```
   python3 bin/echo-stage set-artifact --stage spec
   ```
5. Tell the user to review and approve, then advance with echo-next.

## Under Codex
Gates are advisory and orchestration is prose-driven. See `.agents/skills/README.md` for the
Known limitations before relying on this.
