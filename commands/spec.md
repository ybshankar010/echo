---
description: Generate spec.md (Design stage) from an approved intent.md
---

Produce the Design-stage artifact for the active echo work item.

1. Confirm the intent gate is approved:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status
   ```
   If intent is not approved, STOP and tell me to `/echo:approve` the intent first.
2. Load the `echo:spec-template` skill and read `.echo/artifacts/<ticket>/intent.md`
   (the `Artifacts:` line from `echo-stage status` shows the ticket-scoped folder).
3. Write a full requirements + design spec to `.echo/artifacts/<ticket>/spec.md`, flagging
   any security / compliance / UX concerns. Ground every requirement in the intent; mark
   anything inferred as an assumption.
4. Record it (the path defaults to the ticket-scoped location):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" set-artifact --stage spec
   ```
5. Tell me to review and `/echo:approve`, then `/echo:next`.
