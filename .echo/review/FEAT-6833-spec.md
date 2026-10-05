# Critic re-check: FEAT-6833 spec (revised)

Verdict: no blocking gaps remain. All four prior blockers are resolved.

## Prior blockers
1. post takes --worktree/--base/--head, cleanup after post: resolved (req 4, 5).
2. Fork-safe fetch via pull/<n>/head: resolved (req 4).
3. Strict JSON array, post validates, invalid to dropped: resolved (req 9, Design).
4. PR-mode compliance rescoped to PR's stated intent: resolved (req 8).
Important items (mandatory dry-run + confirm, exit-code contract, anchor edge cases and pure functions, force-push re-resolve, acceptance strengthening, secret/size handling): all addressed.

## Verified against repo
- bin/echo-review-comments exists (own _gh at line 38); bin/echo-watch has _gh at line 50.
- lib/echo_common.py: GH_CALL_TIMEOUT line 340, resolve_pr line 385. No ec.gh / ec.gh_json yet (spec says add them; fine).
- agents/reviewer.md, commands/review.md exist; both Codex mirrors exist (.agents/skills/echo-review/SKILL.md, .codex/agents/reviewer.toml). Neither mirror contains YAGNI today, so AC6 is a real fix.
- tests/test_echo.py loads bin scripts via importlib SourceFileLoader (line 19); smoke.sh has per-bin test -x lines (e.g. line 51).

## Remaining important (non-blocking)
1. Req 8 says compliance uses PR title/description "that prepare captured", but the prepare JSON in req 4 omits title and body (only resolve_pr_by_number returns them). Add title/body to prepare's output or state the command re-reads them.
2. Req 4/11 and AC4 say `post --dry-run` touches no network, but post first re-resolves the head via gh. Either skip re-resolve on dry-run or relax the claim; as written the AC test needs gh stubbed and a real worktree.
3. Force-push re-resolve: findings were produced against the old head; after switching to the new head the diff and line numbers may shift. Spec should say anchors are re-validated against the new diff (filter_findings does this if post diffs the new range) and that stale findings fall to dropped.

## Nits
- `origin/<base>` as diff_range relies on git fetch updating the remote-tracking ref; fetching into a named ref or using FETCH_HEAD for base is safer.
- Remote is assumed to be named `origin`.
- Reviewer runs on untrusted PR content (prompt injection); consider noting the reviewer is read-only and output is validated by post.
- REVIEW.md lookup: from repo root or the worktree? Specify.
