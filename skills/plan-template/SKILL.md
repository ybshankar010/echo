---
name: plan-template
description: The structure and rules for writing an echo plan.md (Build kickoff) from an approved spec.md. Use when running /echo:plan or generating the implementation plan. Produces a single-pass-implementable plan with a concrete Proof section.
---

# plan-template

A `plan.md` is the implementation plan an engineer approves before any code is
written. A good plan lets a different engineer implement it in one pass.

## Required sections
- **Header** — `Ticket:`, `Stage: Build (kickoff)`, `Derived from: spec.md`, `Status:`.
- **Files that change** — every file to create/edit, with a phrase on why.
- **Order of work** — a GitHub checkbox list, one `- [ ]` per top-level step, with the
  step number kept in the text (e.g. `- [ ] 1. ...`); note which steps can run in parallel
  (disjoint files). The build flow flips each box to `- [x]` as its step completes via
  `echo-stage check-next`, and `/echo:status` shows the list plus a done/total count, so keep
  one checkbox per step (sub-bullets stay as plain descriptive text, not counted).
- **Risks** — what could break, and the mitigation for each.
- **Proof** — the exact checks that verify the build: test commands, expected
  results, manual steps. This is what the Test stage runs.
- **Definition of done** — the bar for calling this complete.

## Rules
- Name real files and real functions/utilities to reuse; do not hand-wave.
- The Proof section must be runnable, not aspirational.
- Keep the plan in sync with reality: if the build departs from it, update plan.md.
- No em dashes; lean and concrete.
- Write the prose in Simplified Technical English; load the `echo:ste-writing` skill.

Write to `.echo/artifacts/<ticket>/plan.md` (artifacts are scoped per ticket; the
`Artifacts:` line from `echo-stage status` shows the folder), then
`echo-stage set-artifact --stage plan` (the path defaults to the ticket-scoped location).
Only after I `/echo:approve` the plan does the plan-guard hook allow code edits.
Skeleton: `${CLAUDE_PLUGIN_ROOT}/templates/plan.md`.
