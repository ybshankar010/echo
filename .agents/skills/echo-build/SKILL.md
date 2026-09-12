---
name: echo-build
description: Implement the approved plan via the builder role, with a builder plus reviewer maker-checker refine loop. Use when the stage is build and the plan gate is approved.
---

# echo build (Codex)

Codex port of echo's `/echo:build` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any goal text
(a focus or extra instruction) from what the user typed; never fabricate a ticket.

## Steps
1. Confirm we are ready to build (`python3 bin/echo-stage status`). The stage must be `build`
   and the `plan` gate must be `approved`. If not, STOP and tell the user to approve the plan
   and advance to build first.
2. Read `.echo/config.json` (defaults apply if a key is missing):
   - If `build_driver` is `manual`, tell the user the build is theirs to implement by hand
     and stop here.
   - Read `maker_checker` (`on`/`off`) and `maker_checker_max_iters` (default 2). If
     `maker_checker` is `off`, run the maker once (step 3) and skip the loop (steps 4-5).
3. Maker: delegate in prose to the `builder` role (`.codex/agents/builder.toml`): "Read
   `.echo/artifacts/<ticket>/plan.md` and `.echo/artifacts/<ticket>/spec.md` and implement
   the plan's order of work against the files it names. Reuse existing patterns the plan
   points to. Run the plan's Proof checks where cheap. Fix the code, not the tests. Report
   files changed, checks run with real results, and anything you could not implement." Pass
   along any focus the user gave.
4. Checker: delegate in prose to the `reviewer` role (`.codex/agents/reviewer.toml`): "Read
   REVIEW.md and apply its passes (bugs, security, compliance) to the current working diff
   (`git diff` and staged changes). Report findings ranked by severity, and check the change
   matches `.echo/artifacts/<ticket>/spec.md` and `.echo/artifacts/<ticket>/plan.md`. Do not
   edit any files; report only."
5. Loop: if the reviewer reports important findings (behavior-breaking, data-leaking, or
   policy-breaching) AND you have run the builder fewer than `maker_checker_max_iters` times,
   delegate to a fresh builder with the specific findings as its fix scope, then re-run the
   reviewer (step 4). Stop when the reviewer is clean of important findings or the cap is
   reached. Never weaken a test or the plan to make the loop pass.
6. Write the final checker findings to `.echo/review/<ticket>-build.md` (create the
   `.echo/review/` directory if needed).
7. Summarize for the user: what the builder changed, what the reviewer flagged, how many
   iterations ran, and any important findings that remain. Then tell the user to review the
   change and approve. Do NOT approve for the user.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`builder` and `reviewer` via the Task tool, delegate in prose to `.codex/agents/builder.toml`
and `.codex/agents/reviewer.toml`. See `.agents/skills/README.md` for the Known limitations
before relying on this.
