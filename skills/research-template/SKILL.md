---
name: research-template
description: The structure and rules for writing an echo research.md before work starts. Use when running /echo:research or gathering facts before the intent. Every claim carries a source; nothing is fabricated.
---

# research-template

A `research.md` answers a question before the loop starts, so the intent and spec rest on
verified facts instead of assumptions. It is optional and ungated, but it is only useful if
every claim in it is grounded.

## Required sections
- **Header** - `Question:`, `Date:`, `Ticket or Topic:`, `Status: draft`.
- **Scope** - what the question is and is not asking; what a good answer must decide.
- **Findings** - the facts you gathered. Each finding ends with a `Source:` line: a
  `file:line`, a URL you fetched, a command you ran, or a named system. No source, no finding.
- **Options and tradeoffs** - the viable approaches, with the evidence for and against each.
- **Risks and unknowns** - what you could not verify, stated plainly. This is where "unknown,
  needs verifying" belongs, and it is a valid answer.
- **Recommendation** - the option you would take and why, or "not enough evidence yet" with
  what would resolve it.
- **Sources** - the list of everything cited above (paths, URLs, systems).

## Rules
- Ground every claim. Separate verified fact from inference and label the inference.
- Never fabricate a fact, API, file name, number, or behavior. A confident guess is worse
  than an honest "unknown".
- Prefer primary sources (the code, the doc, the system) over summaries of them.
- No em dashes; lean and concrete.
- Write the prose in Simplified Technical English; load the `echo:ste-writing` skill.

Write to the path `/echo:research` resolved for you (ticket ->
`.echo/artifacts/<ticket>/research.md`; topic -> `.echo/research/<slug>.md`). Research is
supplementary, so there is no `set-artifact` step and no gate.
Skeleton: `${CLAUDE_PLUGIN_ROOT}/templates/research.md`.
