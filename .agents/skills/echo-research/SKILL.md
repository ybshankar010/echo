---
name: echo-research
description: Research a question before work starts, writing a grounded research.md the intent can cite. Use when facts are unknown and need investigating before the loop begins.
---

# echo research (Codex)

Codex port of echo's `/echo:research` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any goal text
from what the user typed; never fabricate a ticket.

## Steps
1. Decide where the research doc goes. If the leading argument is a Jira ticket id
   (`[A-Z]+-[0-9]+`), the research is ticket-scoped; otherwise treat the leading phrase as a
   topic. Resolve the deterministic path (this also creates the folder):
   ```
   # ticket-scoped:
   python3 bin/echo-stage research-path --ticket <TICKET>
   # or topic-first:
   python3 bin/echo-stage research-path --topic "<short topic>"
   ```
   The command prints the repo-relative path to write (ticket ->
   `.echo/artifacts/<ticket>/research.md`; topic -> `.echo/research/<slug>.md`).
2. Delegate the research to the `researcher` role (`.codex/agents/researcher.toml`) in prose:
   "Load the echo research-template skill. Research the question and write the grounded
   result to <the path from step 1>. Put a source on every claim (file:line, a URL you
   fetched, a command you ran, or a named system); label inference as inference; never
   fabricate. Write only that one file under `.echo/`; make no code edits." Pass along the
   full question.
3. Confirm the file was written and show where it is. This does not change the stage or any
   gate; research is supplementary. When ready to start work, echo-intent will read this
   research doc and ground the intent in it.

## Under Codex
Gates are advisory and orchestration is prose-driven. Whether a spawned Codex researcher
gets web tools is unverified. See `.agents/skills/README.md` for the Known limitations
before relying on this.
