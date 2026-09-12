# Spec: Codex compatibility for the echo plugin

- **Ticket:** FEAT-6833
- **Stage:** Design
- **Derived from:** `.echo/artifacts/FEAT-6833/intent.md`
- **Status:** draft (awaiting `/echo:approve`)

## Overview
Make echo usable from OpenAI Codex via research Phase 1, with zero change to the Claude Code
plugin surface. Keep `CLAUDE.md` as the single source of truth and expose its content to Codex
through a relative symlink `AGENTS.md -> CLAUDE.md` (Codex reads only `AGENTS.md` and has no
`@import`). Add a "Using echo from OpenAI Codex" section to `CLAUDE.md` that documents driving the
loop through the stdlib `bin/echo-*` CLIs and running `bin/echo-plan-guard` / `bin/echo-verify-gate`
as manual advisory gates (Codex has no confirmed blocking-hook equivalent). Ship a tiny, testable
fallback for symlink-hostile checkouts. No `bin/`/`lib/` behavior changes; the full commands->Skills
and agents->`agents.*` port is Phase 2 (out of scope).

## Requirements
Each is testable and traces to the intent.

1. **`AGENTS.md` symlink.** Create `AGENTS.md` at repo root as a relative symlink to `CLAUDE.md`.
   Reading `AGENTS.md` returns `CLAUDE.md`'s content; git tracks it as a symlink (mode 120000).
   (Intent: single source of truth via symlink.)
2. **Codex how-to in `CLAUDE.md`.** Add a section "Using echo from OpenAI Codex" that states:
   (a) Codex reads `AGENTS.md`, which is a symlink to this file; (b) the loop is driven by calling
   `bin/echo-*` directly - a concrete command sequence: `echo-stage init --ticket <T> --title ...`
   -> write `intent/spec/plan` -> `echo-stage approve` / `echo-stage next` -> `echo-build` (manual
   or subagent) -> `echo-verify` -> `echo-git ship`; (c) under Codex the gates are ADVISORY - run
   `bin/echo-plan-guard` before editing source and `bin/echo-verify-gate` before ending a turn,
   manually, since Codex has no blocking hook; (d) Jira progress comments are Claude-only (no
   Atlassian MCP wired for Codex), so those steps are skipped. Because `AGENTS.md` symlinks to
   `CLAUDE.md`, this section reaches Codex automatically. (Intent: Codex how-to, manual gates,
   no MCP.)
3. **Symlink-hostile fallback (testable, no drift).** Provide a documented, repeatable way to
   materialize `AGENTS.md` as a real file where symlinks do not survive (Windows checkouts,
   `git archive`): a one-line `cp CLAUDE.md AGENTS.md`, documented in the Codex section with an
   explicit note that it must be re-run whenever `CLAUDE.md` changes (or wired into a local hook).
   No new `bin/` script in this build (keeps scope tight); the symlink is the default. (Intent
   open question: symlink vs generated; leaning symlink default + documented cp fallback.)
4. **No Claude Code regression.** `CLAUDE.md` content is unchanged except the appended Codex
   section; `commands/`, `agents/`, `skills/`, `hooks/`, `bin/`, `lib/` behavior is untouched.
   Existing unit + smoke suites stay green. (Intent: Claude Code users unaffected.)
5. **Core runs under Codex unchanged.** No code change to `bin/echo-*` or `lib/echo_common.py`
   (already stdlib, confirmed). `py_compile` stays clean. (Intent: core runs unchanged.)
6. **Tests cover the new surface.** Add smoke checks (all `$REPO`-qualified, since smoke.sh runs
   inside a temp repo) that `$REPO/AGENTS.md` is a symlink resolving to `CLAUDE.md`, and that
   `$REPO/CLAUDE.md`'s Codex section contains its required substance (the `echo-stage`/`echo-verify`
   sequence, the `echo-plan-guard`/`echo-verify-gate` advisory-gate names, and the no-Jira-on-Codex
   note) - not merely the heading. (Intent: How we know it worked.)

## Design
- **Files changed:**
  - `AGENTS.md` (new) - relative symlink to `CLAUDE.md` (`ln -s CLAUDE.md AGENTS.md`).
  - `CLAUDE.md` (edit) - append the "Using echo from OpenAI Codex" section (req 2 + 3).
  - `README.md` (edit) - one short pointer that echo is Codex-compatible via `AGENTS.md`, linking
    the CLAUDE.md section and the research doc.
  - `tests/smoke.sh` (edit) - assert `AGENTS.md` is a symlink to `CLAUDE.md` and the Codex section
    exists in `CLAUDE.md`.
  - Optionally `tests/test_echo.py` - a unit check is not natural here (this is a repo-file/layout
    concern, not a `lib`/`bin` function), so the smoke test is the primary proof; add a unit test
    only if a pure helper is introduced (none planned).
- **No new `bin/`/`lib/` code**, no `.codex/` scaffold, no config changes. The symlink and a
  documentation section are the whole build.
- **Reuse:** the existing smoke-test harness (`tests/smoke.sh`) and its temp-repo pattern; no new
  test infrastructure.
- **Key decisions (resolving intent open questions):**
  - Symlink is the default mechanism; the cp fallback is documentation only (no new script) to
    keep scope minimal; a generator/hook can be a later enhancement if drift becomes a problem.
  - The Codex how-to lives inside `CLAUDE.md` so the symlinked `AGENTS.md` carries it to Codex.
  - Codex's own symlink handling stays an explicit "verify hands-on" note in the doc, not a
    blocker (the cp fallback covers the failure case).

## Flagged concerns
- **Symlink portability (correctness):** symlinks can break on Windows / `git archive`. Mitigation:
  the documented cp fallback (req 3); the smoke test only asserts the symlink on the dev platform
  where it is created.
- **Advisory gates are weaker (integrity):** under Codex the plan-guard/verify-gate are not
  enforced. Mitigation: the Codex section states this plainly; it is an accepted owner decision,
  not hidden. No security/secret exposure (no new data paths, no MCP on Codex).
- **Drift of a cp-materialized `AGENTS.md`:** a copied file can go stale vs `CLAUDE.md`. Mitigation:
  the doc says re-run on change; the symlink (default) never drifts.
- **Compliance:** no third-party dependency added; no em dashes in the new prose; Jira/ticket
  policy unaffected (this build is on branch `FEAT-6833/codex-compat`).

## Non-goals
- Porting `commands/*.md` to Codex Skills or `agents/*.md` to Codex `agents.*` (Phase 2).
- Wiring any MCP (incl. Atlassian) for the Codex path; no Jira comments under Codex.
- A Codex-native gate approximation via `approval_policy` / `sandbox_mode`.
- Cursor / OpenCode / Copilot support, or a `.codex/` skills scaffold.
- Automated cross-platform symlink handling beyond the documented cp fallback.

## Acceptance criteria
All file checks target the REAL repo path. `tests/smoke.sh` `cd`s into a temp git repo (line 10)
and qualifies real-repo checks with `$REPO/` (e.g. lines 40-47); the new checks MUST do the same
(`$REPO/AGENTS.md`, `$REPO/CLAUDE.md`), never bare paths, or they would inspect the temp repo.

1. `test -L "$REPO/AGENTS.md"` is true and `readlink "$REPO/AGENTS.md"` == `CLAUDE.md` (relative).
2. `cat "$REPO/AGENTS.md"` equals `cat "$REPO/CLAUDE.md"` (read-through). Separately (after the
   file is committed/staged), `git ls-files -s AGENTS.md` shows mode `120000`.
3. The Codex section in `$REPO/CLAUDE.md` is present AND has the required substance - each of these
   greps against `$REPO/CLAUDE.md` succeeds (not just the heading):
   - `grep -q "Using echo from OpenAI Codex" "$REPO/CLAUDE.md"` (the heading);
   - `grep -q "echo-stage" "$REPO/CLAUDE.md"` and `grep -q "echo-verify" "$REPO/CLAUDE.md"` (the
     bin/echo-* driving sequence);
   - `grep -q "echo-plan-guard" "$REPO/CLAUDE.md"` and `grep -q "echo-verify-gate" "$REPO/CLAUDE.md"`
     (the manual advisory-gate steps);
   - `grep -qi "advisory" "$REPO/CLAUDE.md"` (gates are advisory under Codex);
   - a grep confirming the no-Jira/no-MCP-on-Codex note (e.g. `grep -qi "jira" "$REPO/CLAUDE.md"`
     within the Codex section, or an equivalent explicit substring the build chooses and the smoke
     check asserts).
4. `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0 (core unchanged).
5. `python3 -m pytest tests/test_echo.py -q` stays green (was 62 passed; no test weakened).
6. `bash tests/smoke.sh` exits 0 and includes the new `$REPO/AGENTS.md`-symlink and
   Codex-section-substance checks from criteria 1-3.
7. `README.md` mentions Codex compatibility and points to the CLAUDE.md section / research doc.
8. No changes under `commands/`, `agents/`, `skills/`, `hooks/`, `bin/`, `lib/` (verified by
   `git diff --name-only` showing only `AGENTS.md`, `CLAUDE.md`, `README.md`, `tests/smoke.sh`,
   and `.echo/`).

Decision note: the symlink-vs-generator open question is resolved to "symlink default + documented
cp fallback, no new script" for this build; it is surfaced here so the plan gate can override if the
human wants a generator instead.
