# Plan: Plan/build checklist (checkboxes in plan.md Order of work)

- **Ticket:** FEAT-6833
- **Stage:** Build (kickoff)
- **Derived from:** `.echo/artifacts/FEAT-6833/spec.md`
- **Status:** draft (awaiting `/echo:approve`)

## Files that change
- **`lib/echo_common.py`** (edit) - add three pure functions (no IO): `parse_order_checklist`,
  `checklist_counts`, `set_checkbox`.
- **`bin/echo-stage`** (edit) - add subcommands `checklist`, `check`, `uncheck`, `check-next` and
  their `cmd_*` handlers, reusing `_require_state`/`active_item` and the item's `artifacts["plan"]`.
- **`skills/plan-template/SKILL.md`** (edit) - Order of work authored as a `- [ ]` checkbox list.
  Note: `.agents/skills/plan-template` is a SYMLINK to `skills/plan-template` (same inode), so this
  single edit propagates to the Codex plan-template automatically - there is no separate Codex
  plan-template file to change and no drift (verified: `readlink` + same inode).
- **`templates/plan.md`** (edit) - the `## Order of work` example uses checkboxes.
- **`commands/status.md`** (edit) - also run `echo-stage checklist` and show it.
- **`commands/build.md`** (edit) - in-order builder pass calls `echo-stage check-next` per step;
  fix-scope reruns (step 5) explicitly do NOT.
- **`.agents/skills/echo-plan/SKILL.md`**, **`.agents/skills/echo-status/SKILL.md`** (edit) - Codex
  parity (checkbox Order of work; `checklist` subcommand).
- **`tests/test_echo.py`** (edit) - unit tests for the pure fns + the CLI subcommands.
- **`tests/smoke.sh`** (edit) - a `$REPO`-qualified checklist block on a fixture plan.

## Interfaces to build (exact)
### `lib/echo_common.py`
- `parse_order_checklist(text: str) -> list[dict]` - scan the section under a line matching
  `^##\s+Order of work` up to the next `^##\s` heading (or EOF); for each line matching
  `^\s*-\s+\[( |x|X)\]\s+(.*)$` append `{"index": <1-based>, "checked": <bool>, "text": <str>}`.
  No section or no matches -> `[]`.
- `checklist_counts(items) -> tuple[int,int]` -> `(sum(1 for i in items if i["checked"]), len(items))`.
- `set_checkbox(text: str, index: int, checked: bool) -> str` - rewrite ONLY the marker char of the
  1-based index-th Order-of-work checkbox line (`[ ]`->`[x]` or back); everything else on the line
  and in the file is byte-identical. Out-of-range index returns `text` unchanged. Implement by
  walking the same section scan and replacing the first `[ ]`/`[x]` occurrence on the target line.

### `bin/echo-stage` (new subcommands; mirror existing `cmd_*` + argparse style)
- `cmd_checklist`: resolve active item + `artifacts["plan"]`; read file; `items =
  ec.parse_order_checklist(text)`. If no active item / no plan path / file missing / `items == []`
  -> print `checklist: none`, exit 0. Else print `checklist: <done>/<total> done`, then each item
  `f"{i['index']}. [{'x' if i['checked'] else ' '}] {i['text']}"`.
- `cmd_check` / `cmd_uncheck` (`--index`, int, required): read plan; `items = parse`; if not
  `1 <= index <= len(items)` -> stderr error, exit 2; else write `ec.set_checkbox(text, index,
  True/False)` back; print confirmation. No plan/active item -> stderr, exit 2 (manual guard).
- `cmd_check_next`: read plan; find first item with `checked is False`; none -> print
  `checklist: nothing to check`, exit 0; else `set_checkbox(..., idx, True)`, write, print
  `checked: <idx>. <text>`. Fail open (no plan/items -> exit 0, no error).
- Register parsers with `set_defaults(func=...)`; `check`/`uncheck` add `--index` via
  `add_argument("--index", type=int, required=True)`.

## Order of work
- [ ] 1. `lib/echo_common.py`: add `parse_order_checklist`, `checklist_counts`, `set_checkbox` (pure).
- [ ] 2. `bin/echo-stage`: add `checklist` / `check` / `uncheck` / `check-next` subcommands + parsers.
- [ ] 3. `skills/plan-template/SKILL.md` and `templates/plan.md`: Order of work as `- [ ]` checkboxes.
- [ ] 4. `commands/status.md`: invoke `echo-stage checklist` after the status summary.
- [ ] 5. `commands/build.md`: call `check-next` on the in-order pass; state fix-scope reruns do not.
- [ ] 6. `.agents/skills/echo-plan/SKILL.md` + `echo-status/SKILL.md`: Codex parity edits.
- [ ] 7. `tests/test_echo.py`: unit tests for the 3 pure fns + the 4 subcommands.
- [ ] 8. `tests/smoke.sh`: add the `$REPO`-qualified checklist fixture block.
- [ ] 9. Run the full Proof; fix code (not tests) until green.

## Smoke block (insert before the final `echo "ALL SMOKE CHECKS PASSED"`, `$REPO`/`$T`-qualified)
```
echo "== checklist: parse, count, check-next on a fixture plan =="
mkdir -p "$T/.echo/artifacts/FEAT-3816"
printf '## Order of work\n- [ ] 1. first\n- [ ] 2. second\n\n## Proof\n- [ ] not counted\n' \
  > "$T/.echo/artifacts/FEAT-3816/plan.md"
"$BIN/echo-stage" set-artifact --stage plan >/dev/null
"$BIN/echo-stage" checklist | grep -q "checklist: 0/2 done"     # Proof checkbox excluded
"$BIN/echo-stage" check-next | grep -q "checked: 1"
"$BIN/echo-stage" checklist | grep -q "checklist: 1/2 done"
"$BIN/echo-stage" check --index 2 >/dev/null
"$BIN/echo-stage" checklist | grep -q "checklist: 2/2 done"
grep -q -- "- \[x\] 1. first" "$T/.echo/artifacts/FEAT-3816/plan.md"   # text preserved, marker set
```
(The smoke repo's active item is `FEAT-3816` at an advanced stage from earlier steps; `set-artifact
--stage plan` records this fixture as its plan.)

## Risks
- **Wrong-line toggle / text rewrite.** Mitigation: `set_checkbox` changes only the marker char;
  unit test asserts the full line text is byte-identical after toggling, and that Proof-section
  checkboxes are never counted or touched (section scan).
- **`check-next` in the fix loop.** Mitigation (spec req 7): build.md calls it only on the in-order
  pass; fix-scope reruns must not. Stated explicitly in build.md; acceptance greps for the exclusion.
- **Fail-open confusion.** `checklist`/`check-next` never error on a missing plan; only manual
  `check --index`/`uncheck --index` exit 2 on out-of-range. Unit tests cover both.
- **Claude-surface / Codex drift.** Only the listed files change; scope check asserts nothing else.

## Proof (runnable; this is what Test runs)
1. Unit: `parse_order_checklist` parses only the Order-of-work section (Proof checkboxes excluded),
   `[]` when absent; `checklist_counts` correct; `set_checkbox` flips only the marker and is a no-op
   out of range (assert line text unchanged). Run via `pytest`.
2. CLI (temp repo, fixture plan recorded): `echo-stage checklist` -> `checklist: 0/2 done` + list;
   `check-next` -> `checked: 1 ...` then `1/2 done`; `check --index 2` -> `2/2 done`;
   `uncheck --index 1` -> `1/2 done`; `check --index 9` exits 2; no-plan -> `checklist: none`, exit 0.
3. Both files carry checkboxes, checked SEPARATELY (grep of two files passes on either alone):
   `grep -q -- "- \[ \]" skills/plan-template/SKILL.md && grep -q -- "- \[ \]" templates/plan.md`.
   Plus confirm the Codex mirror is the same file: `test -L .agents/skills/plan-template` and
   `grep -q -- "- \[ \]" .agents/skills/plan-template/SKILL.md` (resolves through the symlink).
4. `grep -q "checklist" commands/status.md`; `grep -q "check-next" commands/build.md` AND
   `grep -qi "fix-scope" commands/build.md` (build.md must literally state the fix-scope reruns do
   not call check-next; the builder-instruction and the exclusion both use the word "fix-scope").
5. `grep -qi "checkbox\|checklist" .agents/skills/echo-plan/SKILL.md .agents/skills/echo-status/SKILL.md`.
6. `python3 -m py_compile lib/echo_common.py bin/echo-*` -> exit 0.
7. `python3 -m pytest tests/test_echo.py -q` -> 62 + new tests, all pass (none weakened).
8. `bash tests/smoke.sh` -> ALL SMOKE CHECKS PASSED incl. the new checklist block.
9. `grep -rn "—" lib/echo_common.py bin/echo-stage commands/status.md commands/build.md skills/plan-template/SKILL.md templates/plan.md .agents/skills/echo-plan/SKILL.md .agents/skills/echo-status/SKILL.md` -> no em dashes added.
10. Scope: `git status --porcelain | awk '{print $2}' | grep -vE '^(lib/echo_common\.py$|bin/echo-stage$|skills/plan-template/|templates/plan\.md$|commands/status\.md$|commands/build\.md$|\.agents/skills/echo-(plan|status)/|tests/|\.echo/)'` prints nothing (allowed paths are end-anchored so `bin/echo-stage-x`/`lib/echo_common.pyx` would NOT false-match); nothing under `.claude-plugin/`, other `bin/`, other `lib/`, `agents/`, `commands/` (besides status/build), or `hooks/` is modified.

## Definition of done
- All Proof checks pass; existing 62 tests + all prior smoke assertions stay green (nothing
  weakened); `bin/`/`lib/` stdlib-only.
- Order of work is a checkbox list in the template; `echo-stage checklist`/`check`/`uncheck`/
  `check-next` work and fail open per spec; `/echo:status` shows list + count; build.md auto-checks
  on the in-order pass only.
- `set_checkbox` provably preserves step text; Proof-section checkboxes are never counted.
- Codex `echo-plan`/`echo-status` skills updated; Claude plugin surface otherwise unchanged.
