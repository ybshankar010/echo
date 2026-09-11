---
description: Approve the current stage's artifact (the human gate) so the loop can advance
argument-hint: [stage]
---

I am approving the current stage's artifact. Optional stage override: $ARGUMENTS

1. First show me the current status so I can confirm what I'm approving:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status
   ```
2. Auto-review (flag, does not block): if `approve_review` is `flag` in
   `.echo/config.json` (the default) and the stage being approved is `plan` or `build`,
   run its checker before flipping the gate:
   - `plan`  -> spawn the `critic` subagent over `.echo/artifacts/<ticket>/plan.md` vs
     `.echo/artifacts/<ticket>/spec.md` (the ticket folder is on the `Artifacts:` line of
     `echo-stage status`).
   - `build` -> spawn the `reviewer` subagent over the working diff (its REVIEW.md flow).
   Prefer a fresh `.echo/review/<ticket>-<stage>.md` if one already exists from
   `/echo:plan` or `/echo:build`. If there are important or blocking findings, show them
   and ask me to confirm before approving; do not approve on my behalf. If
   `approve_review` is `off`, skip this step.
3. Then approve the gate. If I named a stage in the argument above, pass it as
   `--stage <that-stage>`; otherwise call it with no flags to approve the current stage:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" approve [--stage <stage>]
   ```
4. Confirm which gate is now approved and remind me to run `/echo:next` to advance.
