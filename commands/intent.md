---
description: Start (or refine) a work item's intent.md — the Plan-stage artifact
argument-hint: <TICKET-ID> <short description of what you want to build>
---

Begin the Plan stage of the echo SDLC loop for: $ARGUMENTS

Do this:
1. Extract a Jira ticket id (`[A-Z]+-[0-9]+`) from the argument. If none is present,
   STOP and ask me for it — never fabricate one (organization policy).
2. Initialize the work item:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" init --ticket <TICKET> --title "<short title>"
   ```
3. Load the intent template skill (`echo:intent-template`) and interview me briefly
   if anything is unclear (problem, outcome, affected systems, constraints, open
   questions). Do not invent facts.
   If prior research exists for this ticket at `.echo/artifacts/<ticket>/research.md`
   (or I point you at a `.echo/research/<slug>.md`), read it first and ground the intent
   in its findings, citing them. Fail open: if there is no research doc, just proceed.
4. Write the result to `.echo/artifacts/<ticket>/intent.md` (the ticket is the one you
   just initialized; the `Artifacts:` line from `echo-stage status` shows the exact
   folder). Then record it (the path defaults to the ticket-scoped location):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" set-artifact --stage intent
   ```
5. Tell me to review it and run `/echo:approve` when it looks right, then `/echo:next`.
