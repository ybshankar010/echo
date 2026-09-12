---
name: echo-review
description: Run the reviewer role over the working diff using REVIEW.md and report findings. Use to review current changes before shipping.
---

# echo review (Codex)

Codex port of echo's `/echo:review` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) from what the user
typed if relevant; never fabricate a ticket.

## Steps
1. Ensure a `REVIEW.md` exists at the repo root. If it does not, offer to copy the template
   from the repo's `templates/REVIEW.md` and use that.
2. Delegate in prose to the `reviewer` role (`.codex/agents/reviewer.toml`): "Read REVIEW.md
   and apply its passes (bugs, security, compliance) to the current working diff (`git diff`
   and staged changes). Report findings ranked by severity, cap nits per REVIEW.md, and check
   the change matches spec.md and plan.md. Do not edit any files; report only."
3. Summarize the findings for the user. Do not treat review findings as auto-approval; the
   user decides what to fix before shipping.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`reviewer` via the Task tool, delegate in prose to `.codex/agents/reviewer.toml`. See
`.agents/skills/README.md` for the Known limitations before relying on this.
