---
name: echo-approve
description: Approve the current stage's artifact, the human gate, so the loop can advance. Use when the user says they approve the current stage.
---

# echo approve (Codex)

Codex port of echo's `/echo:approve` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and an optional
stage override from what the user typed; never fabricate a ticket.

## Steps
1. First show the current status so the user can confirm what they are approving:
   ```
   python3 bin/echo-stage status
   ```
2. Auto-review (flag, does not block): if `approve_review` is `flag` in `.echo/config.json`
   (the default) and the stage being approved is `plan` or `build`, run its checker before
   flipping the gate:
   - `plan` -> delegate in prose to the `critic` role (`.codex/agents/critic.toml`) over
     `.echo/artifacts/<ticket>/plan.md` vs `.echo/artifacts/<ticket>/spec.md`.
   - `build` -> delegate in prose to the `reviewer` role (`.codex/agents/reviewer.toml`) over
     the working diff (its REVIEW.md flow).
   Prefer a fresh `.echo/review/<ticket>-<stage>.md` if one already exists. If there are
   important or blocking findings, show them and ask the user to confirm before approving; do
   not approve on their behalf. If `approve_review` is `off`, skip this step.
3. Then approve the gate. If the user named a stage, pass it as `--stage <that-stage>`;
   otherwise call it with no flags to approve the current stage:
   ```
   python3 bin/echo-stage approve [--stage <stage>]
   ```
4. Confirm which gate is now approved and remind the user to advance with echo-next.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`critic` or `reviewer` via the Task tool, delegate in prose to the matching role under
`.codex/agents/`. See `.agents/skills/README.md` for the Known limitations before relying on
this.
