# Review: FEAT-9999 build (reviewer)

- ts: 2026-09-07
- target: changed files vs `.echo/artifacts/FEAT-9999/{spec,plan}.md` (repo is not git, so files
  were read directly rather than diffed)
- verdict: SOLID after fixes. Proof green: py_compile OK, pytest 45 passed, smoke PASS.

## Findings and resolution
1. (moderate, bug/compliance) `commands/flow.md` did not exclude the `ship` stage from the
   generic per-stage comment step, so at `ship` it could post an undefined `stage:ship` comment
   before the PR exists. FIXED: step 5's stop branch and step 6 now explicitly skip `ship`; the
   ship comment is posted only by `/echo:ship` (event `ship`) after the PR is opened. The only
   step-6 events are `stage:intent|spec|plan|build|test`.
2. (minor, bug) `load_jira_ledger` returned `_read_json(...) or {}`, which passes through valid
   JSON of the wrong type (e.g. a list), so `comment-done` could raise `TypeError` writing to it,
   contradicting the fail-open guarantee. FIXED: it now coerces any non-dict to `{}`
   (`lib/echo_common.py`), covered by a new test `test_jira_ledger_wrong_type_returns_empty`.
3. (nit) An em dash in the new README "Jira progress comments" bullet, against house style.
   FIXED (replaced with a colon).
4. (nit) Mild prose redundancy between flow.md step 5 and step 6. Left as-is (cosmetic).

## Clean passes (reviewer confirmed)
- Security: no secrets/PII; comment templates forbid diffs/tokens; no ticket fabrication; no
  network in `bin/`/`lib/` (only `subprocess` to `git`).
- Compliance: all 10 spec requirements honored; comments-only (no Jira status transitions); MCP
  calls only in the command layer; stdlib-only; dedup / ticketless-skip / no-item-skip /
  per-ticket isolation all tested and passing; version bumped to 0.5.0.
