Ticket: FEAT-6833
Stage: Plan
Author: echo-contributor
Status: draft

# Extend /echo:review to review and comment on a GitHub PR

## Problem
`/echo:review` today only reviews the local working diff: the `reviewer` subagent runs
`git diff` and `git diff --cached`, and the command posts nothing. Reviewing a teammate's
open pull request with the same reviewer is therefore a manual, error-prone dance done by
hand outside the loop: check the PR branch out into a scratch worktree, point the reviewer
at the `base...head` range, hand-build a GitHub review JSON payload, verify every inline
anchor sits on a changed line, and POST it with `gh api`. We just did exactly this for a
teammate's PR, and every step was manual. echo has no one-command way to review a PR or to
publish the reviewer's findings back to it, even though the reviewer agent and the passes
(bugs, security, compliance, YAGNI) are already the thing we want to apply.

## Proposed outcome
`/echo:review` accepts an optional PR target and an opt-in flag to post. With no argument
it behaves exactly as today (working diff, report only). Given a PR, it reviews that PR's
`base...head` diff with the existing reviewer passes and summarizes findings locally; with
the post flag it publishes those findings as a single inline GitHub review (advisory, not
approve/request-changes), anchored to changed lines, with a summary body. Reviewing and
commenting on a colleague's PR becomes one command instead of a manual sequence.

## Affected users / systems
- The `/echo:review` command (`commands/review.md`) and its Codex mirror
  (`.agents/skills/echo-review/SKILL.md`).
- The `reviewer` subagent (`agents/reviewer.md`), which currently hardcodes the
  working-diff selection.
- A deterministic `bin/` helper for the GitHub side (PR resolution, diff range, posting),
  consistent with how `bin/echo-review-comments` and `bin/echo-watch` already wrap `gh`.
- Reviewers using echo against teammates' PRs; the PR authors who receive the comments.

## Constraints
- Backward compatible: no argument means today's behavior, unchanged.
- Posting is opt-in and never silent; a dry run / preview path before anything goes public,
  mirroring the `--dry-run` convention in `echo-git ship` and `echo-review-comments`.
- Follow repo conventions: GitHub/`gh` determinism lives in `bin/` (stdlib only, fail open,
  exit 2 only for intended blocks, executable bit, compile check + tests); command markdown
  stays thin prose. No em dashes. The reviewer agent still reports only and never edits.
- Posted reviews are advisory (event COMMENT), never approve or request-changes, and carry
  no diffs, secrets, or tokens in comment bodies.
- Non-goals: no auto-fixing of PR findings (that is `/echo:address-review`'s job); no change
  to the Jira comment flow; no new review passes.

## Open questions
- Argument shape: positional `<pr-url-or-number>` plus `--comment` to post and `--base` to
  override the base branch? Leaning: yes, matching the `argument-hint` + `$ARGUMENTS`
  convention and argparse in the `bin/` helper.
- How to review the PR without disturbing the user's working tree: a throwaway git worktree
  vs a detached fetch. Leaning: worktree under a temp dir, removed after.
- Should posting require the review to be clean of important findings, or always post what
  the reviewer returns? Leaning: always post what it returns; the human still decides.
- Codex parity: the Codex reviewer mirror still omits YAGNI from its pass list (drift left
  by the prior YAGNI work). Fold that fix in here or leave it. Leaning: fix in passing.

## How we know it worked
- `/echo:review` with no args still reviews the working diff and posts nothing.
- `/echo:review <pr>` reports findings from that PR's `base...head` diff.
- `/echo:review <pr> --comment` (after a preview) publishes one inline review on the PR with
  comments on changed lines, reproducing by command what we just did by hand.
- Unit tests and smoke test stay green; the new `bin/` helper fails open with no `gh`/PR.
