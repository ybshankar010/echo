# Spec: Plan/build checklist (checkboxes in plan.md Order of work)

- **Ticket:** FEAT-6833
- **Stage:** Design
- **Derived from:** `.echo/artifacts/FEAT-6833/intent.md`
- **Status:** draft (awaiting `/echo:approve`)

## Overview
Make the plan's "Order of work" a live checklist (Option A). The `plan-template` authors Order of
work as a GitHub checkbox list (`- [ ] step`); the `/echo:build` flow flips each item to `- [x]`
as its step completes via a deterministic `bin/echo-stage` subcommand; and `/echo:status` prints
the full checklist plus a done/total count. Determinism (parse, toggle, count) lives in
`lib/echo_common.py` + `bin/echo-stage`; only the step wording comes from the model-authored plan.
Fails open everywhere: no plan, no Order-of-work section, or no checkboxes means the feature
no-ops and never blocks the loop.

## Requirements
Each is testable and traces to the intent.

1. **Checkbox parser (pure, in `lib/echo_common.py`).** Add `parse_order_checklist(text) -> list`
   returning, in order, each Order-of-work checkbox as `{index (1-based), checked (bool), text}`.
   It scans only the section under the `## Order of work` heading (up to the next `## ` heading or
   end of file) and matches lines of the form `- [ ] ...` or `- [x] ...` (case-insensitive x). No
   `## Order of work` section, or none matching, returns `[]`. Add `checklist_counts(items) ->
   (done, total)`.
2. **`echo-stage checklist`.** New subcommand: read the active item's plan artifact
   (`item["artifacts"]["plan"]`), parse it, and print `checklist: <done>/<total> done` followed by
   the itemized list (`1. [x] step` / `2. [ ] step`). No active item, no plan file, or no items
   prints `checklist: none` and exits 0 (fail open).
3. **`echo-stage check --index <i>` / `uncheck --index <i>`.** Flip the 1-based i-th Order-of-work checkbox
   in the plan file: change only the single `[ ]`/`[x]` marker character on that line, never the
   line's text. Out-of-range or no plan prints an error and exits 2 (manual-use guard). Idempotent
   (checking a checked item is a no-op success).
4. **`echo-stage check-next`.** Mark the first unchecked Order-of-work item as done and print which
   one; if all are checked (or none exist) it is a no-op that exits 0. This is what the build flow
   calls per completed step.
5. **plan-template authors checkboxes.** Update `skills/plan-template/SKILL.md` and
   `templates/plan.md` so "Order of work" is a `- [ ]` checkbox list (numbered ordering kept in the
   text, e.g. `- [ ] 1. ...`, or plain `- [ ]` items in order). The rule that steps note parallel
   ones is preserved.
6. **`/echo:status` shows the checklist.** Update `commands/status.md` to also run
   `echo-stage checklist` and show the count plus the full list after the stage/gate summary.
7. **Build flow auto-checks, first pass only.** Update `commands/build.md` so that during the
   INITIAL builder pass (which implements the plan's Order of work top to bottom) the builder runs
   `echo-stage check-next` after completing each step, giving live progress. **The reviewer-driven
   fix iterations (build.md step 5, which rerun the builder with only the specific findings as
   scope) MUST NOT call `check-next`** - a fix pass does not walk the Order of work in order, so
   marking "the next unchecked item" there would advance the wrong step. build.md must state this
   explicitly: check-next is called only on the in-order implementation pass, never on fix-scope
   reruns. A manual `echo-stage check --index <i>` / `uncheck --index <i>` override is documented
   for correcting the list. This is best-effort and fail open; no gate depends on it.
8. **Codex parity.** Update `.agents/skills/echo-plan/SKILL.md` and `.agents/skills/echo-status/SKILL.md`
   to reflect the checkbox Order of work and the `checklist` subcommand, so the Codex port stays in
   sync. (Additive; does not touch the Claude Code plugin surface beyond the files listed here.)
9. **Tests updated, no regression.** Add unit tests to `tests/test_echo.py` for the parser, counts,
   `set_checkbox` guard, and the CLI subcommands. Add a `$REPO`-qualified block to `tests/smoke.sh`
   that writes a fixture `plan.md` (with a `## Order of work` checkbox section) into the temp repo,
   records it via `set-artifact --stage plan`, then asserts `echo-stage checklist` reports the
   count/list and `check-next` marks the first unchecked item (mirroring the existing
   `set-artifact`/`echo-verify` pattern in `tests/smoke.sh`). The existing 62 unit tests and all
   prior smoke assertions stay green (this ADDS a block, it does not change existing ones);
   `bin/`/`lib/` stay stdlib-only; no em dashes in new prose. The toggle never rewrites step text
   (guarded), so an approved plan's wording is preserved. `tests/smoke.sh` and `tests/test_echo.py`
   are explicitly among the files this feature changes.

## Design
- **`lib/echo_common.py`:** `parse_order_checklist(text)`, `checklist_counts(items)`, and a small
  helper `set_checkbox(text, index, checked) -> new_text` that rewrites only the marker char of the
  i-th Order-of-work checkbox (returns text unchanged if index out of range). Pure functions, no IO,
  so they unit-test directly like `parse_checks`/`slugify`.
- **`bin/echo-stage`:** `cmd_checklist`, `cmd_check`, `cmd_uncheck`, `cmd_check_next` - each loads
  state, resolves the active item's plan path, reads/writes the file with the pure helpers. Reuse
  the existing active-item resolution and file IO patterns already in the module.
- **Section scoping:** only `## Order of work` is treated as the checklist, so incidental
  checkboxes elsewhere in `plan.md` (e.g. in Proof) are never counted or toggled.
- **Determinism vs plan-guard:** the toggle writes the plan file directly from `bin/` (not via the
  Edit tool), and only the marker char changes; the approved plan content is otherwise untouched.
- **Fail-open contract:** every subcommand degrades to a clean no-op (exit 0, `checklist: none`)
  when there is no active item, no plan artifact recorded, or no Order-of-work checkboxes - except
  the manual `check --index`/`uncheck --index` which exit 2 on an explicit out-of-range request.
- **Key decisions (from intent, owner-locked):** Option A (in `plan.md`); generated with the plan;
  reviewed at the plan gate; auto-checked by the build flow via `check-next`; `/echo:status` shows
  full list + count. Remaining small choices resolved here: one checkbox per top-level Order-of-work
  step (sub-bullets stay as descriptive text, not counted); the flow uses `check-next`
  (mark-next-unchecked) so it needs no step-index bookkeeping; no TodoWrite sync.

## Flagged concerns
- **Mutating an approved `plan.md` during build (integrity):** only the `[ ]`/`[x]` marker char is
  changed, never step text; `set_checkbox` is guarded and unit-tested to prove the line text is
  preserved. This keeps the approved plan's wording intact.
- **Builder reliably calling `check-next` (reliability):** if the builder or flow does not call it,
  items simply stay unchecked - the checklist is then conservative (never falsely "done"), which is
  the safe failure. No gate depends on it.
- **Compliance:** stdlib only; no em dashes; no secrets; Claude plugin surface unchanged except the
  listed additive files; Codex skills updated for parity.

## Non-goals
- A separate checklist file, a TUI/web view, or real-time streaming.
- Syncing with Claude Code's in-session TodoWrite.
- Making the checklist a gate, or auto-marking steps done without the flow/builder actually
  completing them.
- Checkboxes for nested sub-bullets (one checkbox per top-level step only).

## Acceptance criteria
1. Unit: `parse_order_checklist` returns ordered items only from the Order-of-work section, ignores
   checkboxes in other sections, handles missing section/items (returns `[]`); `checklist_counts`
   returns correct `(done,total)`; `set_checkbox` flips only the marker and preserves line text,
   and is a no-op for an out-of-range index.
2. Unit/CLI (temp repo, fixture plan.md): `echo-stage checklist` prints `checklist: <done>/<total> done`
   and the itemized list; with no plan it prints `checklist: none` and exits 0.
3. CLI: `echo-stage check --index 2` sets item 2 to `[x]` (line text unchanged, verified);
   `uncheck --index 2` reverts; an out-of-range index exits 2.
4. CLI: `echo-stage check-next` marks the first unchecked item and reports it; a no-op (exit 0) when
   all are checked.
5. `skills/plan-template/SKILL.md` and `templates/plan.md` show Order of work as `- [ ]` checkboxes.
6. `commands/status.md` invokes `echo-stage checklist`; `commands/build.md` calls `check-next` on
   the in-order build pass and explicitly says fix-scope reruns do NOT (grep build.md for
   `check-next` and for the fix-pass exclusion). `commands/flow.md`'s build stage stays pure
   delegation to `/echo:build`, so it is not required to call `check-next` itself.
7. `.agents/skills/echo-plan/SKILL.md` and `echo-status/SKILL.md` mention the checkbox Order of work
   / `checklist` subcommand (Codex parity).
8. `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0; `python3 -m pytest tests/test_echo.py -q`
   stays green (62 plus the new tests); `bash tests/smoke.sh` passes with a new checklist block.
9. No em dashes in new prose; the Claude plugin manifests and declared surface are otherwise
   unchanged.
