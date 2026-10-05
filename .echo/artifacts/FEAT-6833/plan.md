Ticket: FEAT-6833
Stage: Build (kickoff)
Derived from: spec.md
Status: draft

# Extend /echo:review to review and comment on a GitHub PR

## Files that change
- `lib/echo_common.py` - add shared `gh(args, cwd=None, timeout=GH_CALL_TIMEOUT)` and
  `gh_json(args, cwd=None)` wrappers (one place, so `bin/echo-review-pr` needs no third
  `_gh`); add `resolve_pr_by_number(pr, cwd=None)` plus a pure `_parse_pr_view_full(text)`
  that reads number, baseRefName, headRefName, headRefOid, url, isCrossRepository, title,
  body. Existing `resolve_pr` (385) and `GH_CALL_TIMEOUT` (340) are left untouched.
- `bin/echo-review-pr` - NEW executable CLI (stdlib only), modeled on
  `bin/echo-review-comments`: shebang, `../lib` on `sys.path`, `import echo_common as ec`,
  argparse subcommands `prepare` / `post` / `cleanup`, plus the pure functions
  `new_side_lines`, `filter_findings`, `build_review_payload`, and a `MAX_BODY` truncation
  constant.
- `agents/reviewer.md` - generalize step 1 (lines 12-13): default to `git diff` +
  `git diff --cached`, but use a caller-supplied diff range/command when given, and when the
  caller asks for the PR JSON contract, emit `[{path,line,side,severity,body}]` only. Also
  rework the compliance bullet (step 2) so that in PR mode it checks "matches the PR title
  and description supplied by the caller" rather than reading the active echo
  `.echo/artifacts/<ticket>` spec/plan (spec req 8); the working-diff path keeps the original
  spec/plan compliance check.
- `commands/review.md` - add `argument-hint`, branch on `$ARGUMENTS`: no args keeps today's
  working-diff flow; a PR target drives prepare -> reviewer over the worktree range ->
  `post --dry-run` preview -> human confirm -> `post` -> `cleanup` (cleanup always).
- `.agents/skills/echo-review/SKILL.md` - document the PR arguments and the Codex
  orchestration note; add YAGNI to the pass list.
- `.codex/agents/reviewer.toml` - add YAGNI to the pass list (drift fix).
- `tests/test_echo.py` - add unit tests (pure functions, fail-open CLI, resolve_pr_by_number),
  importing the new script via the `importlib.machinery.SourceFileLoader` pattern used by
  `_load_watch_module` (line 15).
- `tests/smoke.sh` - add a `test -x bin/echo-review-pr` assertion beside the existing per-bin
  checks (lines 51-55).

No change to the loop state machine, gates, hooks, or the Jira flow.

## Order of work
- [x] 1. `lib/echo_common.py`: add `gh` / `gh_json` wrappers, `_parse_pr_view_full`, and
      `resolve_pr_by_number` (fail closed to None). Keep `resolve_pr` unchanged.
- [x] 2. `bin/echo-review-pr`: write the script. Pure functions first (`new_side_lines`,
      `filter_findings`, `build_review_payload`, `MAX_BODY`), then `prepare` (resolve via
      `ec.resolve_pr_by_number`; `git fetch origin <base>` and `git fetch origin
      pull/<n>/head`; `git worktree add --detach <tmp> FETCH_HEAD`; set `diff_range` to
      `origin/<base>...<head_sha>` with FETCH_HEAD as the robust fallback; print the JSON line
      with title/body/diff_range/worktree). If any post-resolve step fails (fetch or
      worktree-add), remove any partial worktree, print nothing, and exit 0 (fail open). Then
      `post` (flags `--pr`, `--worktree`, `--base`, `--head`, `--input`, `--dry-run` per spec
      req 4; requires `--worktree`; with `--worktree` missing or empty it exits 0; dry-run
      skips the gh head re-resolve and all network and prints the payload; real post
      re-resolves head, re-validates anchors against `git -C <worktree> diff <range>`, builds
      payload with `commit_id`, `gh api --method POST .../pulls/<n>/reviews --input <file>`),
      `cleanup` (`git worktree remove --force` with `git worktree prune` fallback; needs a
      repo cwd; fail open). `chmod +x bin/echo-review-pr`.
- [x] 3. `agents/reviewer.md`: generalize the step-1 diff selection (caller range overrides
      the working-diff default), add the PR JSON output contract, and rework the step-2
      compliance bullet so PR mode checks the caller-supplied PR title/description instead of
      the echo spec/plan (spec req 8). State that in PR mode the reviewer runs
      `git -C <worktree> diff <range>` and reads REVIEW.md from the worktree root (inline
      defaults when absent). (Independent of steps 1-2; can run in parallel.)
- [x] 4. `commands/review.md`: add `argument-hint` and the `$ARGUMENTS` branch. Keep the
      no-arg working-diff path verbatim. PR path: parse the PR target and the optional
      `--comment`/`--base` out of `$ARGUMENTS`; run `prepare` and, if it prints nothing
      (fail-open), report that the PR could not be resolved and stop; otherwise spawn the
      reviewer with cwd set to the `worktree` over `diff_range` and the PR title/description;
      write the reviewer's JSON array to a temp file under the system temp dir; show the
      resolved owner/repo/number plus `post --dry-run` preview; post for real only on explicit
      human confirm; then remove the temp file and run `cleanup` unconditionally. (Depends on
      steps 2 and 3 for the wording it cites.)
- [x] 5. Codex mirrors: update `.agents/skills/echo-review/SKILL.md` (PR args + Codex
      orchestration note + YAGNI in the pass list) and `.codex/agents/reviewer.toml` (YAGNI in
      both the pass list and the `description` line). (Independent; can run in parallel.)
- [x] 6. Tests: add the unit tests to `tests/test_echo.py` and the `test -x` line to
      `tests/smoke.sh`. (After steps 1-2.)
- [x] 7. Run Proof (below): compile check, em-dash check, grep scope checks, unit tests,
      smoke test.

## Risks
- Posting to a teammate's PR is outward-facing. Mitigation: `--comment` is opt-in, the real
  `post` runs only after a dry-run preview and explicit human confirm in `commands/review.md`,
  advisory COMMENT only, prose bodies truncated to `MAX_BODY`, no diffs/secrets/tokens.
- A bad inline anchor would 422 the whole review. Mitigation: `filter_findings` keeps only
  on-diff RIGHT-side single-line anchors and folds the rest into the summary body, verified
  by a pure-function unit test.
- Force-push between prepare and post. Mitigation: real `post` re-resolves the head and
  re-validates anchors against the new diff (dry-run does neither, staying network-free).
- Reviewer reads untrusted PR content (prompt injection). Mitigation: `post` is the
  validator of record and can only emit an advisory COMMENT of prose findings.
- Worktree leak. Mitigation: `commands/review.md` calls `cleanup` unconditionally; unique
  temp dir per run.

## Proof
Run from repo root; all must pass.
1. Compile: `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0.
2. Executable + help: `test -x bin/echo-review-pr` and
   `bin/echo-review-pr --help` lists `prepare`, `post`, `cleanup`.
3. Unit tests: `python3 -m pytest tests/test_echo.py -q` passes, including the new cases:
   `new_side_lines` parses a sample unified diff; `filter_findings` keeps an on-diff RIGHT
   finding and drops an off-diff/LEFT/malformed one; `build_review_payload` is COMMENT with
   one comment per kept finding and dropped folded into the body (and truncates an over-long
   body); `prepare` with no gh prints nothing and exits 0; `post --dry-run --input <file>`
   (fixture: a temp git repo with a one-commit diff for the anchors, or an injected diff
   string) prints a payload, exits 0, no network; `post` with no `--worktree` exits 0;
   `cleanup` on a missing worktree exits 0; `ec.resolve_pr_by_number` returns None when gh
   fails.
4. Smoke: `bash tests/smoke.sh` passes (includes the new `test -x bin/echo-review-pr`).
5. Backward compat: `grep -n "argument-hint" commands/review.md` matches and the no-arg
   working-diff wording is retained.
6. Codex parity:
   `grep -l "YAGNI" .agents/skills/echo-review/SKILL.md .codex/agents/reviewer.toml` lists
   both; reviewer range wording present: `grep -n "range" agents/reviewer.md` matches.
7. PR-mode compliance rescope present (spec req 8): `agents/reviewer.md` and
   `commands/review.md` each mention checking the PR title/description in PR mode
   (`grep -in "PR title" agents/reviewer.md commands/review.md` matches both), so no echo
   spec/plan compliance finding is posted on a teammate's PR.
8. No em dashes in changed files: grep for the em dash over `commands/review.md`,
   `agents/reviewer.md`, `bin/echo-review-pr`, `lib/echo_common.py`,
   `.agents/skills/echo-review/SKILL.md`, `.codex/agents/reviewer.toml` returns nothing.

## Definition of done
- `/echo:review` with no args is unchanged; `<pr>` reviews the PR diff; `<pr> --comment`
  posts one advisory inline review after a previewed confirm.
- All GitHub/git determinism is in `bin/echo-review-pr` + `lib/echo_common.py`; command and
  agent markdown stay thin.
- Proof steps 1 to 8 pass; no `bin/` script loses its executable bit; no em dashes added.
