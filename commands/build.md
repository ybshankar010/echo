---
description: Implement the approved plan via the builder subagent, with a maker-checker refine loop
argument-hint: [-- <focus or extra instruction>]
---

Drive the Build stage for the active echo work item: the `builder` subagent implements
the approved plan, the `reviewer` subagent critiques the result, and the builder revises
until it is clean or the iteration cap is hit. This is the maker-checker loop.

1. Confirm we are ready to build:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status
   ```
   The stage must be `build` and the `plan` gate must be `approved`. If not, STOP and
   tell me to `/echo:approve` the plan and `/echo:next` to reach build first. Do not
   force anything.
2. Read the config at `.echo/config.json` (defaults apply if a key is missing):
   - If `build_driver` is `manual`, tell me the build is mine to implement by hand and
     stop here (the plan-guard already allows code edits at this stage).
   - Read `maker_checker` (`on`/`off`) and `maker_checker_max_iters` (default 2). If
     `maker_checker` is `off`, run the maker once (step 3) and skip the loop (steps 4-5).
3. Maker: spawn the `builder` subagent (Task tool) with this instruction: "Read
   `.echo/artifacts/<ticket>/plan.md` and `.echo/artifacts/<ticket>/spec.md` (the ticket
   folder is on the `Artifacts:` line of `echo-stage status`) and implement the plan's
   order of work against the files it names. Reuse existing patterns the plan points to.
   Run the plan's Proof checks where cheap. Fix the code, not the tests. After completing
   each top-level step of the plan's Order of work, run
   `python3 \"${CLAUDE_PLUGIN_ROOT}/bin/echo-stage\" check-next` to flip that step's
   checkbox to done for live progress (fail open: it no-ops if there are no checkboxes).
   This auto-check happens only on this in-order implementation pass. Report files
   changed, checks run with real results, and anything you could not implement." Pass
   along: $ARGUMENTS
4. Checker: spawn the `reviewer` subagent (Task tool) with: "Read REVIEW.md and apply its
   passes (bugs, security, compliance, YAGNI) to the current working diff (`git diff` and staged
   changes). Report findings ranked by severity, and check the change matches
   `.echo/artifacts/<ticket>/spec.md` and `.echo/artifacts/<ticket>/plan.md`. Do not edit
   any files; report only." Substitute the active `<ticket>` from `echo-stage status`.
5. Loop: if the reviewer reports important findings (behavior-breaking, data-leaking, or
   policy-breaching) AND you have run the builder fewer than `maker_checker_max_iters`
   times, spawn a fresh `builder` subagent with the specific findings as its fix scope,
   then re-run the reviewer (step 4). Stop when the reviewer is clean of important
   findings or the cap is reached. Never weaken a test or the plan to make the loop pass.
   These fix-scope reruns MUST NOT call `echo-stage check-next`: a fix-scope pass does not
   walk the Order of work top to bottom, so marking "the next unchecked item" there would
   advance the wrong step. `check-next` runs only on the in-order pass of step 3. To
   correct the checklist by hand, use `echo-stage check --index <i>` / `uncheck --index <i>`.
6. Record the final reviewer report for grounding:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status
   ```
   Write the final checker findings to `.echo/review/<ticket>-build.md` (create the
   `.echo/review/` directory if needed; `<ticket>` is the active item's id from status).
7. Summarize for me: what the builder changed, what the reviewer flagged, how many
   iterations ran, and any important findings that remain. Then tell me to review the
   change and `/echo:approve` when I am satisfied. Do NOT approve for me.
