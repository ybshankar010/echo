---
name: echo-plan
description: Generate plan.md (Build kickoff) from an approved spec.md, then run the critic maker-checker loop. Use when the spec gate is approved and an implementation plan is needed.
---

# echo plan (Codex)

Codex port of echo's `/echo:plan` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any goal text
from what the user typed; never fabricate a ticket.

## Steps
1. Confirm the spec gate is approved (`python3 bin/echo-stage status`). If not, STOP and tell
   the user to approve the spec first.
2. Load the `echo:plan-template` skill and read `.echo/artifacts/<ticket>/spec.md`
   (the `Artifacts:` line from `echo-stage status` shows the ticket-scoped folder).
3. Write `.echo/artifacts/<ticket>/plan.md`: files that change, order of work, risks, and a
   concrete Proof section (the exact checks that will verify the build). Aim for a plan a
   different engineer could implement single-pass.
4. Record it:
   ```
   python3 bin/echo-stage set-artifact --stage plan
   ```
5. Maker-checker loop (unless `maker_checker` is `off` in `.echo/config.json`): delegate in
   prose to the `critic` role (`.codex/agents/critic.toml`): "Check
   `.echo/artifacts/<ticket>/plan.md` against `.echo/artifacts/<ticket>/spec.md` for
   coverage, feasibility, testability, and risk honesty. Report blocking gaps ranked by
   severity; do not edit." If it reports blocking gaps and you have revised fewer than
   `maker_checker_max_iters` times (default 2), reload the `echo:plan-template` skill, revise
   the plan to close them, re-record it (step 4), and re-run the critic. Stop when clean or
   at the cap. Then write the final critic findings to `.echo/review/<ticket>-plan.md`.
6. Invite the user to interrogate the plan (riskiest step? what breaks? alternatives?) and
   approve when solid.

## Under Codex
Gates are advisory and orchestration is prose-driven. The plan-guard hook that gates code
edits is Claude-only; under Codex treat "no code before an approved plan" as advisory. Where
the Claude command spawns the `critic` via the Task tool, delegate in prose to
`.codex/agents/critic.toml`. See `.agents/skills/README.md` for the Known limitations before
relying on this.
