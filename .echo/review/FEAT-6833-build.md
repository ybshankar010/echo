# Build review: FEAT-6833 (address code review comments)

- Timestamp: 2026-09-21
- Reviewer pass: bugs / security / compliance over the working diff
- Result: no blocking, no important findings.

## Verified clean
- Ticket enforcement: `echo-git followup` exits 2 with no ticket and on base/main/master.
- `followup` never rebases and never runs `gh pr create` (only add/commit/push + `gh pr view`).
- Fail-open discipline across `echo-review-comments` (every early return exits 0).
- `resolve --dry-run` touches no network and writes no ledger.
- Ticket regex prevents path-separator injection into ledger/artifact paths.
- GraphQL calls use argv lists (no shell), correct `-f`/`-F` types; no shell-injection surface.
- One-line truncation on every stored/printed body; ledger stores id/status/ts/commit only.
- No em dashes introduced; executable bits present on the new CLI.
- Implementation matches spec/plan requirements 1-10 point for point.

## Minor nits
- Fixed: null `line` rendered as `path:None` (now shows just the path via `_loc`).
- Fixed: base-branch followup test now pins the branch name (no dependency on
  `init.defaultBranch`).
- Accepted (documented limitations): GraphQL `reviewThreads(first:100)` has no pagination
  (a PR with >100 threads drops the overflow); the stage/commit block is duplicated between
  `ship` and `followup`; the `resolve_pr` two-call glue is not directly unit-tested (its pure
  parsers are).

## Proof
- `python3 -m py_compile lib/echo_common.py bin/echo-*` -> exit 0.
- `python3 -m pytest tests/test_echo.py -q` -> 95 passed.
- `bash tests/smoke.sh` -> ALL SMOKE CHECKS PASSED.
