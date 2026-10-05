Ticket: FEAT-6833
Stage: Design
Derived from: intent.md
Status: draft

# Extend /echo:review to review and comment on a GitHub PR

## Overview
Give `/echo:review` an optional PR target so the existing `reviewer` subagent can review a
pull request's `base...head` diff, and an opt-in flag to publish its findings as one
advisory inline GitHub review. The GitHub determinism (resolving the PR, preparing a
throwaway worktree, parsing diff anchors, building and posting the payload) lives in a new
stdlib `bin/echo-review-pr`, with the shared `gh` plumbing added once to
`lib/echo_common.py` so no wrapper is duplicated. The command markdown stays thin
orchestration and the reviewer agent still reports only. With no argument, behavior is
identical to today (working diff, report only).

## Requirements
1. `/echo:review` with no arguments reviews the working diff (`git diff` + `git diff
   --cached`) and posts nothing, exactly as today. (intent: Constraints, backward compatible)
2. `/echo:review <pr-url-or-number>` reviews that PR's `base...head` diff with the PR-mode
   passes (see req 8) and reports findings locally, posting nothing. (intent: Proposed outcome)
3. `/echo:review <pr-url-or-number> --comment` publishes the reviewer's findings as a single
   GitHub review with `event=COMMENT` (never approve or request-changes), a summary body, and
   inline comments anchored to changed lines. It MUST show a dry-run preview and get explicit
   user confirmation before the real post (req 6). (intent: Proposed outcome; Constraints)
4. New `bin/echo-review-pr` (Python 3 stdlib only, executable, imports `echo_common as ec`)
   owns all `gh`/git calls via three subcommands:
   - `prepare --pr <url|number> [--base <branch>]`: resolve the PR in the current repo
     (`ec.resolve_pr_by_number`, which runs `gh pr view <pr> --json
     number,baseRefName,headRefName,headRefOid,url,isCrossRepository` plus `gh repo view
     --json owner,name`). Fetch the base and the PR head by the fork-safe ref
     (`git fetch origin <base>` and `git fetch origin pull/<n>/head`), then
     `git worktree add --detach <tmp> FETCH_HEAD`. Print one JSON line with
     `{number, owner, repo, base_ref, head_sha, worktree, diff_range, title, body}` where
     `diff_range` is `origin/<base>...<head_sha>` and `title`/`body` are the PR's stated
     intent (consumed by the req 8 compliance rescope). A `--base` override is reflected in
     `base_ref`/`diff_range` so later steps inherit it.
   - `post --pr <n> --worktree <path> --base <branch> --head <sha> --input <findings.json>
     [--dry-run]`: for a real post, re-resolve the current PR head and, if it differs from
     `--head`, re-fetch into the worktree, use the current head, and re-validate anchors
     against the new diff (stale ones fall to `dropped`), so a force-push between prepare and
     post does not cause a 422. This re-resolve is skipped under `--dry-run`, which performs
     no network calls. Validate findings against the diff (req 7); build the payload with
     `commit_id = <resolved head>`; `gh api --method POST repos/<owner>/<repo>/pulls/<n>/reviews
     --input <file>`. `--dry-run` prints the payload and posts nothing.
   - `cleanup --worktree <path>`: `git worktree remove --force <path>` (fail open).
5. Orchestration order in `commands/review.md` for PR mode is fixed:
   prepare -> spawn reviewer over `diff_range` in the `worktree` -> `post --dry-run`
   (preview) -> user confirms -> `post` (real) -> `cleanup`. `cleanup` runs unconditionally,
   including when the reviewer, preview, or post fails, so no worktree leaks.
6. `commands/review.md` gains `argument-hint` and branches on `$ARGUMENTS`: no args is the
   working-diff path (req 1); a PR target drives req 5. The real post happens only after the
   human confirms the dry-run preview, mirroring the `--dry-run`-first idiom in `ship.md` and
   `address-review.md`. (intent: Proposed outcome; Constraints, previewed)
7. Anchor validation lives in pure, importable functions in `bin/echo-review-pr`, unit
   tested without network:
   - `new_side_lines(diff_text) -> {path: set[int]}` parses unified-diff hunks and collects
     only RIGHT-side (added and context) line numbers per new-file path.
   - `filter_findings(findings, anchors) -> (kept, dropped)` keeps single-line RIGHT-side
     findings whose `path:line` is in `anchors`; everything else (LEFT/deleted lines,
     renames, binary files, off-diff lines, malformed entries) goes to `dropped`.
   - `build_review_payload(head_sha, summary, kept, dropped) -> dict` builds the COMMENT
     review; dropped findings are folded into the summary body as text, never lost. Comment
     and summary bodies are truncated to a safe length (GitHub's limit) and carry prose only,
     never diffs, secrets, or tokens.
8. PR mode rescopes the passes so nothing false is posted publicly: bugs, security, and YAGNI
   apply; the compliance pass is NOT the echo `.echo/artifacts/<ticket>` spec/plan check (that
   is meaningless for a teammate's PR) but a "matches the PR's stated intent" check using the
   PR title and description that `prepare` captured. The working-diff path (req 1) keeps the
   original compliance-vs-spec/plan pass. (intent: Constraints, no false findings)
9. The reviewer emits findings for PR mode as a strict JSON array
   `[{path, line, side, severity, body}]` (side defaults RIGHT). `commands/review.md` tells
   the reviewer this output contract explicitly; `bin/echo-review-pr post` validates each
   entry (required keys and types) and routes any invalid or off-diff entry to `dropped`
   rather than raising. (intent: Affected systems)
10. `agents/reviewer.md` step 1 is generalized: review `git diff` + `git diff --cached` by
    default, but if the invoking command supplies an explicit diff range or command (and,
    for PR mode, an output contract), use that instead. Still reports only; never edits.
11. Fail-open and exit-code contract:
    - `prepare` with no `gh`, no auth, no remote, or an unresolvable PR prints nothing and
      exits 0.
    - `post --dry-run`, or `post` with nothing valid to post, touches no network and exits 0.
    - A genuine `gh` POST failure exits 1 so the command reports it. The script never exits 2
      (reserved for blocking hooks).
12. Codex parity: `.agents/skills/echo-review/SKILL.md` documents the PR arguments and states
    that under Codex the orchestrator itself runs the prepare/post/cleanup CLIs (no Task tool;
    the reviewer sandbox is read-only). Both it and `.codex/agents/reviewer.toml` list the
    pass set as `bugs, security, compliance, YAGNI`, fixing the pre-existing YAGNI drift.
    (intent: Open questions 4)

## Design
- `bin/echo-review-pr` follows `bin/echo-review-comments`: `#!/usr/bin/env python3`, adds
  `../lib` to `sys.path`, imports `echo_common as ec`, argparse subcommands, executable bit
  tracked. To avoid a third duplicated `gh` wrapper (one each in echo-review-comments and
  echo-watch today), add a shared `ec.gh(args, cwd=None, timeout=ec.GH_CALL_TIMEOUT)` and
  `ec.gh_json(args, cwd=None)` to `lib/echo_common.py` and use them here; the two existing
  scripts are left as-is (not refactored in this change) to keep scope tight.
- `ec.resolve_pr_by_number(pr, cwd)` is a new helper beside the existing branch-based
  `ec.resolve_pr` (unchanged). It returns
  `{number, owner, repo, base_ref, head_sha, head_ref, is_cross_repository, title, body}` or
  None (fail closed). `prepare` and `post` both call it.
- Worktree + diff reproduce, deterministically, the manual flow we used by hand: fetch the
  base and `pull/<n>/head`, detached worktree at the head, review diff `origin/<base>...
  <head_sha>`, remove the worktree after. The temp dir is unique per run.
- Reviewer handoff: the reviewer returns the JSON array (req 9); `commands/review.md` writes
  it to a temp file and passes it to `post`. The bin script is the single place that talks to
  `gh`; the model only produces the array, and `post` is the validator of record.
- Posting payload: `{commit_id, event:"COMMENT", body, comments:[{path, line, side, body}]}`
  via `gh api --method POST`. This is exactly the call we ran manually, now parameterized.

## Flagged concerns
- External publication (security/etiquette): posting lands on a colleague's PR and notifies
  them. Mitigation: opt-in (`--comment`), mandatory dry-run preview plus explicit confirm
  (reqs 3, 6), advisory COMMENT only, prose-only bodies with no diffs/secrets/tokens and
  size truncation (req 7). The rescoped compliance pass (req 8) stops false "does not match
  echo spec" findings from ever being posted.
- Wrong-repo / wrong-PR: the command runs in the target repo's working dir; `prepare` prints
  the resolved `owner/repo/number` in the preview so the user confirms before any post.
- Worktree leakage: `cleanup` runs unconditionally after the review (req 5); unique temp dir.
- Force-push between prepare and post: `post` re-resolves the head and posts against the
  current head to avoid a 422 (req 4).
- Token/auth: delegated entirely to `gh`; the script never reads or logs tokens.
- Prompt injection: the reviewer reads untrusted PR content, so a PR could try to steer its
  output. Mitigation: `post` is the validator of record (req 9) and only ever emits an
  advisory COMMENT review of prose findings; it cannot be driven to approve, merge, or run
  anything. REVIEW.md is read from the prepared worktree root (the PR's own tree), falling
  back to the reviewer's inline defaults when absent. The remote is assumed to be `origin`.

## Non-goals
- No auto-fixing of PR findings (that remains `/echo:address-review`'s job).
- No change to the Jira comment flow, the echo loop state machine, or the gates.
- No new review passes, and no change to severity or the nit cap.
- No approve/request-changes reviews; advisory COMMENT only.
- No refactor of the existing `gh` wrappers in echo-review-comments / echo-watch.
- No special fork handling beyond `pull/<n>/head` and what `gh` resolves by default.

## Acceptance criteria
1. `commands/review.md` has an `argument-hint` and a no-argument path that still spawns the
   reviewer over the working diff (`grep -n "argument-hint" commands/review.md` matches; the
   working-diff wording is retained).
2. `bin/echo-review-pr` exists, is executable (`test -x bin/echo-review-pr`),
   `python3 -m py_compile bin/echo-review-pr` exits 0, and `bin/echo-review-pr --help` lists
   `prepare`, `post`, `cleanup`.
3. Pure functions are importable and unit tested in `tests/test_echo.py` (import the script
   via `importlib` as the suite already does for `bin/echo-*`):
   - `new_side_lines` parses a sample unified diff to the correct `{path: {lines}}`.
   - `filter_findings` keeps an on-diff RIGHT finding and routes an off-diff line, a LEFT
     finding, and a malformed entry to `dropped`.
   - `build_review_payload` yields `event=="COMMENT"`, the given `commit_id`, one comment per
     kept finding, and the dropped findings folded into `body`; over-long bodies are truncated.
4. Network-free CLI tests mirror `test_review_comments_fetch_fail_open_no_pr`: with `gh`
   stubbed to fail (or absent on PATH), `prepare` prints nothing and exits 0; `post
   --dry-run --input <file>` prints a payload and exits 0 touching no network; `cleanup` on a
   missing worktree exits 0. `ec.resolve_pr_by_number` returns None when `gh` fails.
5. `agents/reviewer.md` step 1 states the default working-diff behavior and that an explicit
   range/command from the caller overrides it (`grep -n "range" agents/reviewer.md` matches).
6. `.agents/skills/echo-review/SKILL.md` documents the PR arguments and the Codex
   orchestration note, and both it and `.codex/agents/reviewer.toml` contain `YAGNI` in the
   pass list (`grep -l "YAGNI" .agents/skills/echo-review/SKILL.md .codex/agents/reviewer.toml`
   lists both).
7. `tests/smoke.sh` gains an assertion that `bin/echo-review-pr` exists and is executable,
   alongside the existing per-bin checks.
8. No em dashes in any changed file (`grep -n` for the em dash over commands/review.md,
   agents/reviewer.md, bin/echo-review-pr, lib/echo_common.py, .agents/skills/echo-review/SKILL.md,
   .codex/agents/reviewer.toml returns nothing).
9. `python3 -m pytest tests/test_echo.py -q` and `bash tests/smoke.sh` stay green;
   `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0.
