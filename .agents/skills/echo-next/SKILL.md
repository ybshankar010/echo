---
name: echo-next
description: Advance to the next SDLC stage and generate its artifact, blocking if the current gate is not approved. Use to move the loop forward after approving a stage.
---

# echo next (Codex)

Codex port of echo's `/echo:next` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) from what the user
typed if relevant; never fabricate a ticket.

## Steps
1. Attempt to advance:
   ```
   python3 bin/echo-stage next
   ```
2. If it exits non-zero (gate not approved), STOP and tell the user to review the current
   artifact and approve first. Do not force anything.
3. If it prints `advanced:<stage>`, act on that stage:
   - `spec` -> load the `echo:spec-template` skill; read `.echo/artifacts/<ticket>/intent.md`;
     write `.echo/artifacts/<ticket>/spec.md`; record with
     `python3 bin/echo-stage set-artifact --stage spec`.
   - `plan` -> load the `echo:plan-template` skill; read `.echo/artifacts/<ticket>/spec.md`;
     write `.echo/artifacts/<ticket>/plan.md`; record with
     `python3 bin/echo-stage set-artifact --stage plan`; then run the plan maker-checker loop
     as in echo-plan (delegate to the `critic` role, revise up to `maker_checker_max_iters`,
     write `.echo/review/<ticket>-plan.md`).
   - `build` -> tell the user the plan is approved and to run the echo-build flow (unless
     `build_driver` is `manual`, in which case they implement by hand).
   - `test` -> tell the user to run the echo-verify flow.
   - `ship` -> tell the user to run the echo-ship flow.
4. After generating an artifact, tell the user to review it and approve when ready.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`critic` via the Task tool, delegate in prose to `.codex/agents/critic.toml`. See
`.agents/skills/README.md` for the Known limitations before relying on this.
