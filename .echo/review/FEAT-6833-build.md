Ticket: FEAT-6833
Stage: Build (checker report)
Reviewer: echo:reviewer over the working diff + untracked bin/echo-review-pr
Iterations: 2 builder passes (implement, then fix), reviewer clean of important findings

# Extend /echo:review to review and comment on a GitHub PR - build review

Passes applied: bugs, security, compliance, YAGNI (inline defaults; no root REVIEW.md).

## Important findings
None remaining. The first reviewer pass raised two important issues, both fixed in the
second builder pass and confirmed resolved:
1. Wrong-repo / wrong-PR on a URL target: `_parse_owner_repo_from_url` + `_reconcile_pr_repo`
   in lib/echo_common.py now fail closed (return None) when a PR URL's repo differs from the
   cwd repo; a plain PR number still uses the cwd repo.
2. `new_side_lines` in bin/echo-review-pr now parses the `@@ -a,b +c,d @@` header and tracks
   remaining new-side lines, so a deleted `--- old` or added `+++` line inside a hunk no
   longer ends the hunk or resets the path.

Also fixed in the same pass: exit-code contract (argparse exit 2 and uncaught exceptions map
to 0 via `_run_main`; only genuine gh POST failure exits 1), `cleanup` path guard
(`_is_safe_worktree` restricts to the temp dir + `echo-review-pr-` prefix), required
`--base`/`--head` for a real post, and stale-head refresh skipping the post on a failed
fetch/checkout.

## Spec / plan compliance
Matches spec reqs 1-12 and plan: executable bit, prepare/post/cleanup subcommands, fail-open
prepare, unconditional cleanup in the command markdown, Codex parity (YAGNI added to both
mirrors), and the PR-mode compliance rescope in agents/reviewer.md.

## Nits (none blocking)
- `git fetch origin pull/<n>/head` assumes `origin` is the gh-resolved repo; a fork origin
  vs upstream could pull a different PR with the same number (not covered by the repo
  reconcile). Follow-up candidate.
- `post --pr` is assumed a bare number; `prepare` always emits the number, so the normal flow
  is fine, but a URL passed directly to `post` is unvalidated.
- `--dry-run` with `--head` but no `--base` yields an empty `origin/None...` anchor set (all
  findings dropped in the printed payload); no network touched.
- `post` does not apply `_is_safe_worktree` (read-only git/gh in that cwd; low risk).
- C-quoted `+++` paths (special characters) are not unquoted, so such files fold into the
  summary rather than anchoring (safe degradation).

## Verification observed
- `python3 -m pytest tests/test_echo.py -q`: 110 passed.
- `bash tests/smoke.sh`: ALL SMOKE CHECKS PASSED.
- `python3 -m py_compile lib/echo_common.py bin/echo-*`: exit 0.
- No em dashes in the changed files.
