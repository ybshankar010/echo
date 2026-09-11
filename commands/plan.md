---
description: Generate plan.md (Build kickoff) from an approved spec.md
---

Produce the Build-stage implementation plan for the active echo work item.

1. Confirm the spec gate is approved (`echo-stage status`). If not, STOP and tell me
   to `/echo:approve` the spec first.
2. Load the `echo:plan-template` skill and read `.echo/artifacts/<ticket>/spec.md`
   (the `Artifacts:` line from `echo-stage status` shows the ticket-scoped folder).
3. Write `.echo/artifacts/<ticket>/plan.md`: files that change, order of work, risks, and
   a concrete Proof section (the exact checks that will verify the build). Aim for a
   plan a different engineer could implement single-pass.
4. Record it (the path defaults to the ticket-scoped location):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" set-artifact --stage plan
   ```
5. Maker-checker loop (unless `maker_checker` is `off` in `.echo/config.json`): spawn the
   `critic` subagent (Task tool) with: "Check `.echo/artifacts/<ticket>/plan.md` against
   `.echo/artifacts/<ticket>/spec.md` for coverage, feasibility, testability, and risk
   honesty. Report blocking gaps ranked by severity; do not edit." If it reports blocking
   gaps and you have revised fewer than `maker_checker_max_iters` times (default 2), reload
   the `echo:plan-template` skill, revise the plan to close them, re-record it (step 4), and
   re-run the critic. Stop when clean or at the cap. Then write the final critic findings to
   `.echo/review/<ticket>-plan.md` (`<ticket>` from `echo-stage status`).
6. Invite me to interrogate the plan (riskiest step? what breaks? alternatives?) and
   `/echo:approve` when solid. Only after the plan gate is approved will the
   plan-guard hook allow code edits.
