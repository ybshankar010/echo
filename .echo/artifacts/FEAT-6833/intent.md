# Intent: Plan/build checklist (a live todo of exactly what the loop is doing)

- **Ticket:** FEAT-6833
- **Stage:** Plan
- **Author:** echo-contributor
- **Status:** draft (awaiting `/echo:approve`)

## Problem
When echo runs the Plan and Build stages, the concrete steps live inside `plan.md`'s "Order of
work" section as static prose. During `/echo:build` the builder subagent executes those steps,
but the developer cannot see, at a glance, exactly which steps are done, in progress, or pending.
There is no durable, checkable todo list tied to the plan. The developer wants a checklist they
can watch so they know precisely what the loop is doing at any moment, rather than inferring it
from prose or a subagent's final report.

## Proposed outcome
echo turns the plan's "Order of work" into a live checklist and keeps it current as the build
proceeds. Decisions locked with the owner (2026-09-14):
- **The checklist lives inside `plan.md` (Option A).** The plan's "Order of work" is authored as a
  GitHub checkbox list (`- [ ] step`), generated together with `plan.md` at the Plan stage. There
  is no separate checklist file; the checklist IS the plan's steps, so it cannot drift.
- It is reviewed under the **existing plan gate** - no separate checklist approval. The developer
  sees it when reviewing the plan and edits/flags it there if they want changes.
- **The build flow auto-checks items.** As `/echo:build` completes each Order-of-work step, a
  deterministic `bin/` helper flips that item from `- [ ]` to `- [x]` in `plan.md`, with a manual
  toggle available as override. Only checkbox state is mutated, never the plan's wording.
- **`/echo:status` shows the full checklist plus a count** (for example "build: 3/8 steps done"
  followed by the itemized list), so the developer sees exactly what the loop has done and what
  remains.
- Determinism stays in `bin/`/`lib/`: parsing the Order-of-work list, toggling a checkbox, and
  counting state are deterministic CLI work; only the step wording comes from the model-authored
  plan.

## Affected users / systems
- **Developer** running `/echo:plan` / `/echo:build` / `/echo:status`: gains a live todo view of
  the loop.
- **echo internals (to be designed in spec):** the `plan-template` skill updated so "Order of
  work" is authored as a `- [ ]` checkbox list; a `bin/echo-stage` (or sibling) subcommand to
  toggle/count checkbox items in `plan.md` deterministically; a `/echo:status` addition that
  prints the count plus the full list; and a touchpoint in the `/echo:build` flow that flips each
  item as its step completes. No separate checklist artifact.
- No change intended to the Claude Code plugin's public behavior beyond adding this surface, and
  it must remain Codex-portable (the `plan` skill port would inherit the checkbox convention).

## Constraints
- Stdlib Python only; no third-party dependency. No em dashes in user-facing strings/docs.
- Determinism belongs in `bin/`/`lib/`; do not make the checklist a purely model-driven artifact
  that can drift from the plan. The items must trace to the plan's Order of work.
- Fail open, like every echo gate: if there is no plan or no Order of work to parse, the feature
  does nothing and never blocks the loop.
- Do not weaken or replace the existing gates; this is an additive visibility aid, not a new gate.
- Keep it consistent with how echo already stores state (committed JSON/markdown under `.echo/`).
- Non-goals (for this item): a fancy TUI or web view; real-time streaming; replacing Claude
  Code's in-session TodoWrite (this is echo's own durable artifact, complementary to it);
  auto-generating steps that are not in the plan.

## Open questions
Resolved with the owner (2026-09-14): location = checkboxes in `plan.md` (Option A); generated
with the plan; reviewed at the existing plan gate (no separate approval); auto-checked by the
`/echo:build` flow with a manual override; `/echo:status` shows the full list plus a count. Only
these spec-level details remain:
- **Nested sub-bullets:** the Order of work sometimes has sub-bullets under a numbered step. Does
  each top-level step become one checkbox (sub-bullets stay as descriptive text under it), or do
  sub-bullets also get checkboxes? Leaning: one checkbox per top-level step; keep it simple.
- **How the flow knows which step just finished:** the build flow completes steps in order, so the
  simplest mapping is "mark the next unchecked item" after each step, vs matching by index. Leaning:
  mark-by-index if the flow can pass the step number, else next-unchecked. Decide in spec/plan.
- **Manual toggle ergonomics:** `echo-stage check <n>` / `uncheck <n>` by 1-based index, and how
  it handles an out-of-range index (fail open). Settle the exact CLI shape in spec.
- **Relationship to Claude Code TodoWrite:** keep echo's `plan.md` checklist as the source of
  truth and leave the in-session TodoWrite as an independent, unsynced convenience. Leaning: no
  sync (sync is fragile); confirm in spec.

## How we know it worked
- After `/echo:plan`, `plan.md`'s "Order of work" is a `- [ ]` checkbox list (Option A; no separate
  checklist file), one checkbox per top-level step.
- During/after `/echo:build`, completed steps show as checked and `/echo:status` reports progress
  (e.g. a done/total count) for the active item.
- With no plan or no parseable Order of work, the feature no-ops and the loop is unchanged (fail
  open).
- Existing unit tests + smoke stay green; new tests cover checklist generation, toggling, and the
  status/no-op paths. Determinism lives in `bin/`/`lib/`, verifiable without the model.
