---
name: echo-review
description: Run the reviewer role over the working diff using REVIEW.md and report findings. Use to review current changes before shipping.
---

# echo review (Codex)

Codex port of echo's `/echo:review` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments, so read them from what the user typed. With no PR
target, review the working diff (below). A PR target is a PR url or number; `--comment`
opts in to posting; `--base <branch>` overrides the base. Read the ticket id
(`[A-Z]+-[0-9]+`) from what the user typed if relevant; never fabricate a ticket.

## Steps (no PR target: working-diff review)
1. Ensure a `REVIEW.md` exists at the repo root. If it does not, offer to copy the template
   from the repo's `templates/REVIEW.md` and use that.
2. Delegate in prose to the `reviewer` role (`.codex/agents/reviewer.toml`): "Read REVIEW.md
   and apply its passes (bugs, security, compliance, YAGNI) to the current working diff
   (`git diff` and staged changes). Report findings ranked by severity, cap nits per
   REVIEW.md, and check the change matches spec.md and plan.md. Do not edit any files; report
   only."
3. Summarize the findings for the user. Do not treat review findings as auto-approval; the
   user decides what to fix before shipping.

## Steps (a PR target: PR review)
GitHub/git work goes through the stdlib `bin/echo-review-pr` CLI. Under Codex there is no Task
tool and the reviewer sandbox is read-only, so the orchestrator itself runs the
prepare/post/cleanup CLIs (do not expect the reviewer role to run gh or git):
1. `bin/echo-review-pr prepare --pr <target> [--base <branch>]`. If it prints nothing (fail
   open), report that the PR could not be resolved and stop. Otherwise parse the JSON line.
2. Delegate in prose to the `reviewer` role to review `git -C <worktree> diff <diff_range>`
   with the bugs, security, YAGNI, and PR-compliance passes, checking the change against this
   PR's `title`/`body` (not any echo spec/plan), and to emit only a strict JSON array
   `[{path, line, side, severity, body}]`.
3. Summarize the findings. If `--comment` was not given, stop (report only).
4. With `--comment`: write the array to a temp file, run `bin/echo-review-pr post ... --dry-run`
   to preview the payload, and post for real (same command without `--dry-run`) only after the
   user confirms.
5. Remove the temp file and run `bin/echo-review-pr cleanup --worktree <worktree>`
   unconditionally so no worktree leaks.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`reviewer` via the Task tool, delegate in prose to `.codex/agents/reviewer.toml`; the
orchestrator runs the `bin/echo-review-pr` CLIs itself. See `.agents/skills/README.md` for the
Known limitations before relying on this.
