---
description: Run the reviewer subagent over the working diff or a GitHub PR using REVIEW.md
argument-hint: "[<pr-url-or-number>] [--comment] [--base <branch>]"
---

Review a change before shipping. With no argument, review the local working diff and
report only. With a PR target, review that pull request's diff; add `--comment` to
publish the findings as one advisory GitHub review after a previewed confirm.

Write the reviewer summary prose in Simplified Technical English (load `echo:ste-writing`).

Branch on `$ARGUMENTS`:

## No argument: working-diff review (unchanged)

1. Ensure a `REVIEW.md` exists at the repo root. If it does not, offer to copy the
   template from `${CLAUDE_PLUGIN_ROOT}/templates/REVIEW.md` and use that.
2. Spawn the `reviewer` subagent (Task tool) with: "Read REVIEW.md and apply its
   passes (bugs, security, compliance, YAGNI) to the current working diff (`git diff` and
   staged changes). Report findings ranked by severity, cap nits per REVIEW.md, and
   check the change matches spec.md and plan.md. Do not edit any files; report only."
3. Summarize the findings for me. Do not treat review findings as auto-approval; I
   decide what to fix before `/echo:ship`.

## A PR target: PR review (optionally comment)

Parse the PR target (url or number) and the optional `--comment` and `--base <branch>`
out of `$ARGUMENTS`. All GitHub/git work goes through `bin/echo-review-pr`; this
command only orchestrates. Run from the target repo's working directory.

1. `prepare`: run `bin/echo-review-pr prepare --pr <target> [--base <branch>]`. If it
   prints nothing (fail open: no gh/auth/remote, or an unresolvable PR), report that the
   PR could not be resolved and stop. Otherwise parse its JSON line for `number`,
   `owner`, `repo`, `base_ref`, `head_sha`, `worktree`, `diff_range`, `title`, `body`.
2. Review: spawn the `reviewer` subagent (Task tool) with its cwd set to `worktree` and
   tell it: review the PR diff via `git -C <worktree> diff <diff_range>`, apply the
   bugs, security, YAGNI, and PR-compliance passes, and for compliance check the change
   against the PR title and description (quote the `title` and `body` from `prepare`)
   rather than any echo spec/plan. Give it the PR JSON output contract: emit only a
   strict JSON array `[{path, line, side, severity, body}]`, `side` defaulting to
   `RIGHT`, and nothing else.
3. Summarize the findings for me. If `--comment` was not given, stop here (report only,
   nothing is posted).
4. If `--comment` was given, write the reviewer's JSON array to a temp file under the
   system temp dir, then preview: run
   `bin/echo-review-pr post --pr <number> --worktree <worktree> --base <base_ref>
   --head <head_sha> --input <tmpfile> --dry-run`. Show me the resolved
   `owner/repo#number` and the dry-run payload. Post for real only after I explicitly
   confirm, by re-running the same command without `--dry-run`.
5. Cleanup: remove the temp file and run `bin/echo-review-pr cleanup --worktree
   <worktree>` unconditionally, including when the reviewer, preview, or post failed, so
   no worktree leaks.
