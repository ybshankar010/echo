# Plan: Codex compatibility for the echo plugin

- **Ticket:** FEAT-6833
- **Stage:** Build (kickoff)
- **Derived from:** `.echo/artifacts/FEAT-6833/spec.md`
- **Status:** draft (awaiting `/echo:approve`)

## Files that change
- **`CLAUDE.md`** (edit) - append a new section `## Using echo from OpenAI Codex` with the
  required substance (spec req 2/3): that `AGENTS.md` is a symlink to this file; the concrete
  driving sequence via the CLIs (`bin/echo-stage init` -> write `intent/spec/plan` ->
  `bin/echo-stage approve`/`next` -> `bin/echo-verify` -> `bin/echo-git ship`); that gates are
  ADVISORY under Codex - run `bin/echo-plan-guard` before editing source and `bin/echo-verify-gate`
  before ending a turn, manually; and that Jira progress comments are Claude-only (no Atlassian MCP
  on Codex). Must literally contain the strings the smoke greps check: `Using echo from OpenAI
  Codex`, `echo-stage`, `echo-verify`, `echo-plan-guard`, `echo-verify-gate`, `advisory`, and the
  no-Jira note must use the literal phrase `Atlassian MCP` (e.g. "no Atlassian MCP is wired for
  Codex, so Jira progress comments are skipped") - this phrase is absent elsewhere in CLAUDE.md,
  so a section-scoped grep for it genuinely enforces the note (a whole-file `grep jira` would be a
  false positive against the pre-existing ticket-policy text at CLAUDE.md:19). Include the cp
  fallback: `cp CLAUDE.md AGENTS.md` for symlink-hostile checkouts, with a note to re-run on
  change. No em dashes in the new prose (repo convention).
- **`AGENTS.md`** (new) - a relative symlink to `CLAUDE.md`, created from the repo root with
  `ln -s CLAUDE.md AGENTS.md` (so `readlink` returns exactly `CLAUDE.md`).
- **`README.md`** (edit) - one short line under an appropriate heading: echo is Codex-compatible
  via `AGENTS.md` (symlink to CLAUDE.md); point to the CLAUDE.md section and
  `.echo/research/adopt-echo-plugin-to-codex.md`.
- **`tests/smoke.sh`** (edit) - add a check block before the final `ALL SMOKE CHECKS PASSED`
  line (72), all `$REPO`-qualified (the script runs inside a temp repo `$T`).

## Order of work
1. Append the `## Using echo from OpenAI Codex` section to `CLAUDE.md` (source of truth first, so
   the symlink target has the content). (foundation)
2. From the repo root, create the symlink: `ln -s CLAUDE.md AGENTS.md`. (depends on 1 existing)
3. Add the README pointer. (parallel with 4)
4. Add the smoke-test block (below). (after 1-2 so it passes when run)
5. `git add -A` so the symlink is staged (required before the `git ls-files -s` mode check).
6. Run the full Proof; fix content (not tests) until green.

### Exact smoke.sh addition (insert before line 72 `echo "ALL SMOKE CHECKS PASSED"`)
```
echo "== codex: AGENTS.md is a symlink to CLAUDE.md =="
test -L "$REPO/AGENTS.md"
test "$(readlink "$REPO/AGENTS.md")" = "CLAUDE.md"
diff <(cat "$REPO/AGENTS.md") "$REPO/CLAUDE.md" >/dev/null

echo "== codex: CLAUDE.md has the Codex how-to with substance =="
grep -q "Using echo from OpenAI Codex" "$REPO/CLAUDE.md"
grep -q "echo-stage" "$REPO/CLAUDE.md"
grep -q "echo-verify" "$REPO/CLAUDE.md"
grep -q "echo-plan-guard" "$REPO/CLAUDE.md"
grep -q "echo-verify-gate" "$REPO/CLAUDE.md"
grep -qi "advisory" "$REPO/CLAUDE.md"
# no-Jira/no-MCP note, scoped to the new section so it can't pass on the pre-existing
# "Jira ticket id" policy text at CLAUDE.md:19 (a whole-file `grep jira` is a false positive):
sed -n '/## Using echo from OpenAI Codex/,$p' "$REPO/CLAUDE.md" | grep -qi "atlassian mcp"
```
(These mirror the existing `$REPO/`-qualified checks at smoke.sh:40-47; they never touch `$T`.
The CLAUDE.md Codex section MUST contain the literal phrase "Atlassian MCP" in its no-Jira note,
which is absent elsewhere in CLAUDE.md today, so this grep genuinely enforces the new content.)

## Risks
- **Symlink created non-relative or wrong target.** Mitigation: create it from the repo root as
  `ln -s CLAUDE.md AGENTS.md` (not an absolute path), so `readlink` == `CLAUDE.md`; the smoke test
  asserts exactly this.
- **Codex section missing a required substring** -> a substance grep fails. Mitigation: the plan
  lists every required string; write them verbatim into the section.
- **A whole-file `grep jira` is a FALSE POSITIVE.** CLAUDE.md:19 already says "Jira ticket id",
  so a bare `grep jira` passes even if the maker omits the Codex no-MCP note. Mitigation (applied):
  the check is section-scoped and greps for the unique phrase `Atlassian MCP`
  (`sed -n '/## Using echo from OpenAI Codex/,$p' | grep -qi "atlassian mcp"`), which is absent
  elsewhere in CLAUDE.md, so it only passes when the new section actually carries the note.
- **Committing the symlink.** `git add -A` stages it as mode `120000`; verify with
  `git ls-files -s AGENTS.md`. On the (out-of-scope) Windows case, the cp fallback is documented.
- **Accidental Claude Code regression.** Mitigation: only append to CLAUDE.md; touch no
  `commands/agents/skills/hooks/bin/lib`; acceptance criterion 8 checks the diff scope.

## Proof (runnable; this is what Test runs)
1. `test -L AGENTS.md && [ "$(readlink AGENTS.md)" = CLAUDE.md ]` -> true (from repo root).
2. `diff <(cat AGENTS.md) CLAUDE.md` -> no output (read-through); after `git add -A`,
   `git ls-files -s AGENTS.md` shows `120000`.
3. `grep -q "Using echo from OpenAI Codex" CLAUDE.md` and the substance greps
   (`echo-stage`, `echo-verify`, `echo-plan-guard`, `echo-verify-gate`, `advisory`) succeed
   against `CLAUDE.md`, and the section-scoped no-MCP grep
   `sed -n '/## Using echo from OpenAI Codex/,$p' CLAUDE.md | grep -qi "atlassian mcp"` succeeds.
4. `python3 -m py_compile lib/echo_common.py bin/echo-*` -> exit 0.
5. `python3 -m pytest tests/test_echo.py -q` -> 62 passed (unchanged; no test weakened).
6. `bash tests/smoke.sh` -> `ALL SMOKE CHECKS PASSED`, exit 0, including the new codex block.
7. `grep -qi codex README.md` -> succeeds; the line points to the CLAUDE.md section / research doc.
8. `git diff --name-only` (plus untracked `AGENTS.md`) shows only `AGENTS.md`, `CLAUDE.md`,
   `README.md`, `tests/smoke.sh`, and `.echo/` - nothing under `commands/agents/skills/hooks/bin/lib`.
9. No em dashes in the new prose: `grep -n "—" CLAUDE.md README.md` returns nothing new from this
   change (repo convention).

## Definition of done
- All Proof checks pass; existing 62 tests stay green (no test weakened, no code in `bin/`/`lib/`
  changed).
- `AGENTS.md` is a committed symlink (mode 120000) resolving to `CLAUDE.md`; reading it yields the
  CLAUDE.md content including the Codex section.
- `CLAUDE.md`'s Codex section documents the CLI driving sequence, the manual advisory gates
  (named), and the no-Jira-on-Codex note.
- `README.md` advertises Codex compatibility and links the details.
- No Claude Code plugin behavior changed; the diff is limited to the files named above.
