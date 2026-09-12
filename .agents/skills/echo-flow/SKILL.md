---
name: echo-flow
description: Drive the whole echo SDLC loop from a single goal, auto-advancing clean stages and stopping only at the gates that matter. Use when the user wants to run or resume the full loop for a ticket.
---

# echo flow (Codex)

Codex port of echo's `/echo:flow` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any goal text
from what the user typed; never fabricate a ticket.

## Steps
This reduces the loop to a few touchpoints: run the mechanical work, auto-approve any stage
whose automated check comes back clean, and stop only where a human decision matters. It is
re-runnable: read `echo-stage status` and continue from wherever the item is.

### Setup
1. Extract a Jira ticket id (`[A-Z]+-[0-9]+`) from what the user typed. If none is present,
   STOP and ask for it. Never fabricate one (organization policy).
2. Read `.echo/config.json`. The `autonomy` level decides which gates to stop at
   (`gated` -> every stage; `checkpoint` (default) -> `plan` and `ship`; `auto` -> `ship`
   and any failure). Do not decide this yourself; ask the bin
   (`python3 bin/echo-stage gate-mode --stage <stage>`) per stage.
3. If research was requested, run the echo-research flow first so the intent can cite it.
4. If there is no active item yet (or it is a different ticket), run the echo-intent flow to
   initialize and write `.echo/artifacts/<TICKET>/intent.md`.

### Drive loop
Repeat until the item reaches `done` or you hit a stop:

1. Run `python3 bin/echo-stage status` to see the current stage and gate.
2. If the current stage's artifact/action is not done yet, produce it with the matching
   flow: spec -> echo-spec; plan -> echo-plan (with its critic maker-checker loop);
   build -> echo-build (the builder + reviewer maker-checker loop); test -> echo-verify;
   ship -> handled at the stop below.
3. Run the stage's automated check and read its result (intent/spec/plan use the critic,
   build uses the reviewer, test uses the echo-verify exit code).
4. If the check FAILED (important/blocking findings, or verify non-zero): STOP. Summarize
   what failed, do NOT approve, and say how to fix or override. A failed check always stops,
   whatever the autonomy level.
5. Otherwise ask the bin whether to pause: `python3 bin/echo-stage gate-mode --stage <current-stage>`.
   - `stop` -> summarize the artifact and the clean check result and STOP. Tell the user to
     review and approve, and that re-running the flow resumes from here. At `ship`, once
     approved, run the echo-ship flow, then run the mandatory post-ship watch if
     `.echo/verify/<TICKET>-ci.md` does not exist yet
     (`python3 bin/echo-watch run --ticket <TICKET>`).
   - `auto` -> approve and advance without the user:
     `python3 bin/echo-stage approve` then `python3 bin/echo-stage next`, then continue.

Under Claude Code this command also posts per-stage Jira progress comments through the
Atlassian MCP tools. That is Claude-only; skip it under Codex.

### On every stop
State plainly: the ticket, the stage you stopped at, why (a gate or a failure), what to
review, and how to resume. Do not auto-approve a stop gate, and do not weaken any check to
keep moving.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`critic`, `builder`, or `reviewer` via the Task tool, delegate in prose to the matching role
under `.codex/agents/`. See `.agents/skills/README.md` for the Known limitations before
relying on this.
