---
name: intent-template
description: The structure and rules for writing an echo intent.md (Plan stage). Use when starting a new work item, capturing a problem into intent.md, or running /echo:intent. Keeps intent grounded, ticketed, and gate-ready.
---

# intent-template

An `intent.md` captures a problem in the originator's own words and turns it into a
committed, reviewable artifact. Keep it short and honest; it is the seed of the loop.

## Required sections
- **Header** — `Ticket:` (a real `[A-Z]+-[0-9]+`, never fabricated), `Stage: Plan`,
  `Author:`, `Status:` (draft until approved).
- **Problem** — what hurts today, in plain language. No solution yet.
- **Proposed outcome** — what "better" looks like when this ships.
- **Affected users / systems** — who and what this touches.
- **Constraints** — scope boundaries, non-negotiables, explicit non-goals.
- **Open questions** — anything unresolved, each with your current leaning.
- **How we know it worked** — a few leading signals.

## Rules
- Do not invent facts, systems, or numbers. If unknown, put it in Open questions.
- One ticket per intent. If the work spans tickets, ask which one this is.
- Write for a reviewer who has five minutes: lead with the problem and outcome.
- No em dashes; keep it lean and concrete.
- Write the prose in Simplified Technical English; load the `echo:ste-writing` skill.

Write the file to `.echo/artifacts/<ticket>/intent.md` (artifacts are scoped per ticket
so separate work items never overwrite each other; the `Artifacts:` line from
`echo-stage status` shows the exact folder), then record it with
`echo-stage set-artifact --stage intent` (the path defaults to the ticket-scoped location).
A copy of the skeleton lives at `${CLAUDE_PLUGIN_ROOT}/templates/intent.md`.
