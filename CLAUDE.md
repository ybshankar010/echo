# echo — plugin repo

A personal Claude Code plugin implementing an AI-native SDLC loop
(Plan -> Design -> Build -> Test -> Ship) for a single developer.

## Building enhancements (the echo way)
This repo is built with echo itself, so dogfood it: drive every non-trivial enhancement
through echo's own loop instead of editing ad hoc. The active work item lives in `.echo/`.

- One command: `/echo:flow <TICKET-ID> <goal>` drives the whole loop (research? -> intent
  -> spec -> plan -> build -> test -> ship), auto-advancing stages whose check is clean and
  stopping at the `plan` and `ship` gates (the default `checkpoint` autonomy). Re-run it to
  continue after you approve a gate.
- Or step by step: `/echo:research` (optional, when facts are unknown) -> `/echo:intent
  <TICKET> <goal>` -> review -> `/echo:approve` -> `/echo:next` (spec) -> ... -> `/echo:build`
  -> `/echo:verify` -> `/echo:ship`. `/echo:status` shows where you are and the next action.
- No code before an approved `plan.md`: the plan-guard hook blocks source edits until the
  plan gate is approved, so write intent -> spec -> plan first.
- Every change carries a Jira ticket id (`[A-Z]+-[0-9]+`); never fabricate one. Ship stays
  gated on a green `/echo:verify`, and commits/PRs use `TICKET: <desc>` with the
  Co-Authored-By trailer.
- The Plan and Build stages run a maker-checker loop (`critic` / `builder` + `reviewer`);
  let those catch gaps before you approve rather than skipping the gate.

## Commands
- Unit tests: `python3 -m pytest tests/test_echo.py -q`
- Smoke test: `bash tests/smoke.sh`
- Compile check: `python3 -m py_compile lib/echo_common.py bin/echo-*`

## Architecture
- `lib/echo_common.py` — all shared determinism (paths, `TICKET_RE`, stage list,
  JSON state/config I/O, stack detection, git helpers). Everything imports it.
- `bin/echo-*` — one CLI per concern; `#!/usr/bin/env python3`, executable, no `.py`
  extension. Each adds `../lib` to `sys.path` and imports `echo_common as ec`.
- `hooks/hooks.json` — wires SessionStart/PostCompact/PreToolUse/Stop/SessionEnd.
- `commands/*.md`, `agents/*.md`, `skills/*/SKILL.md` — thin orchestration over `bin/`.
- State lives in the target repo's `.echo/` (committed): `state.json`, `config.json`,
  `artifacts/<TICKET>/` (intent/spec/plan/research, scoped per ticket), `verify/`,
  `review/`, `research/`, `recap.md`, `episodes.jsonl`.

## Conventions
- Python 3, standard library only — no third-party dependency (no PyYAML; state is JSON).
- Determinism belongs in `bin/`/`lib/`; only prose generation is model-driven.
- Every gate FAILS OPEN when it cannot map an active item (never brick a repo).
- Ticket regex is `[A-Z]+-[0-9]+`; never fabricate a ticket id (organization policy).
- No em dashes in user-facing strings or docs.

## Things to get right
- Hooks block with exit code 2; anything else must exit 0 or it looks like a failure.
- `bin/` scripts must stay executable (`chmod +x`) — the git worktree tracks the bit.
- After editing a `bin/` CLI, run the compile check and the relevant test before done.

## Verifying your work
- Run the unit tests and smoke test above before reporting done; paste the output.
- Fix the code, not the tests.
