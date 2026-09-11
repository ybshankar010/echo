---
description: Advance to the next SDLC stage and generate its artifact (blocks if the current gate is not approved)
---

Advance the echo loop one stage.

1. Attempt to advance:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" next
   ```
2. If it exits non-zero (gate not approved), STOP and tell me to review the current
   artifact and run `/echo:approve` first. Do not force anything.
3. If it prints `advanced:<stage>`, act on that stage:
   - `spec`  -> load the `echo:spec-template` skill; read
     `.echo/artifacts/<ticket>/intent.md`; write `.echo/artifacts/<ticket>/spec.md`;
     record with `echo-stage set-artifact --stage spec` (path defaults to ticket-scoped).
   - `plan`  -> load the `echo:plan-template` skill; read
     `.echo/artifacts/<ticket>/spec.md`; write `.echo/artifacts/<ticket>/plan.md`; record
     with `echo-stage set-artifact --stage plan`; then run the plan maker-checker loop as
     in `/echo:plan` (spawn the `critic`, revise up to `maker_checker_max_iters`, write
     `.echo/review/<ticket>-plan.md`). The `<ticket>` and folder come from
     `echo-stage status` (its `Artifacts:` line).
   - `build` -> tell me the plan is approved and to run `/echo:build`, which implements
     the plan via the `builder` subagent with a maker-checker loop (unless `build_driver`
     is `manual` in `.echo/config.json`, in which case I implement by hand).
   - `test`  -> tell me to run `/echo:verify`.
   - `ship`  -> tell me to run `/echo:ship`.
4. After generating an artifact, tell me to review it and `/echo:approve` when ready.
