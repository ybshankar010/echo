---
description: Run the reviewer subagent over the working diff using REVIEW.md
---

Review the current changes before shipping.

1. Ensure a `REVIEW.md` exists at the repo root. If it does not, offer to copy the
   template from `${CLAUDE_PLUGIN_ROOT}/templates/REVIEW.md` and use that.
2. Spawn the `reviewer` subagent (Task tool) with: "Read REVIEW.md and apply its
   passes (bugs, security, compliance) to the current working diff (`git diff` and
   staged changes). Report findings ranked by severity, cap nits per REVIEW.md, and
   check the change matches spec.md and plan.md. Do not edit any files; report only."
3. Summarize the findings for me. Do not treat review findings as auto-approval —
   I decide what to fix before `/echo:ship`.
