# Build review: FEAT-6833 — Mandatory post-ship CI and review monitoring

- ts: 2026-09-12
- stage: build (maker-checker complete)
- iterations: 2 builder passes, 2 reviewer passes
- result: CLEAN of important findings

## Maker-checker summary
- Builder (pass 1) implemented the plan: new `bin/echo-watch` (checks/comments/run),
  `commands/watch.md`, `parse_checks`/`watch_artifact_path`/config keys in `lib/echo_common.py`,
  the `watch_gate` in `bin/echo-stage` `cmd_next`, and edits to `commands/ship.md`,
  `commands/flow.md`, `README.md`, plus tests. Proof: 58 passed, smoke green.
- Reviewer (pass 1) raised two important findings.
- Builder (pass 2) fixed both plus two minors. Proof: 62 passed, smoke green.
- Reviewer (pass 2) confirmed both fixed with no regressions.

## Important findings (both CONFIRMED-FIXED)
1. Unbounded `gh` call could overrun `--max-wait` (a single hung call blocked forever),
   contradicting the spec's "must never block unbounded". Fixed: `GH_CALL_TIMEOUT = 30`;
   `_gh`/`_gh_available` pass a per-call `timeout=` and catch `subprocess.TimeoutExpired`
   returning the gh-failure sentinel; `poll_checks` caps each call at
   `min(GH_CALL_TIMEOUT, deadline - now)`; the opt-in `--watch` blocking mode is deliberately
   uncapped (`timeout=None`). Tests: `test_watch_gh_timeout_branch_fails_open`,
   `test_watch_run_fail_open_on_gh_timeout`.
2. `--ticket` was not validated (path-traversal write outside `.echo/verify/`). Fixed:
   `_validate_ticket` (`ec.TICKET_RE.fullmatch`, `sys.exit(2)`) called before any path/ledger
   use in `cmd_checks`/`cmd_comments`/`cmd_run`. Test: `test_watch_run_rejects_bad_ticket`
   (asserts exit 2 and nothing written outside `verify/`).

## Minors handled
- `--interval`/`--max-wait` <= 0 rejected (`_validate_poll`, `sys.exit(2)`);
  test `test_watch_run_rejects_nonpositive_poll`.
- New-code em dash removed from `bin/echo-watch` and `commands/watch.md`.

## Compliance (re-confirmed clean)
- Parameterized ledger keys `ci:failed:<sha>` / `review:seen:<id>` (spec §7).
- `review_bot_login` unset -> list-all, post-none.
- `watch_gate` at the `ship -> done` advance in `cmd_next`, fail-open.
- No secrets/tokens/diffs in artifact or Jira; Jira status never changed.
- Stdlib only; `bin/echo-watch` executable; `run` always exits 0 on the default path.

## Proof (real, verified by main session)
- `python3 -m py_compile lib/echo_common.py bin/echo-*` -> exit 0
- `test -x bin/echo-watch` -> executable
- `python3 -m pytest tests/test_echo.py -q` -> 62 passed (was 45; +17 across the build)
- `bash tests/smoke.sh` -> ALL SMOKE CHECKS PASSED, exit 0
