---
description: Research a question before work starts, writing a grounded research.md the intent can cite
argument-hint: <TICKET-ID | topic> <question>
---

Do grounded research before the echo loop starts, for: $ARGUMENTS

1. Decide where the research doc goes. If the first argument is a Jira ticket id
   (`[A-Z]+-[0-9]+`), the research is ticket-scoped; otherwise treat the leading phrase as a
   topic. Resolve the deterministic path (this also creates the folder):
   ```
   # ticket-scoped:
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" research-path --ticket <TICKET>
   # or topic-first:
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" research-path --topic "<short topic>"
   ```
   The command prints the repo-relative path to write (ticket ->
   `.echo/artifacts/<ticket>/research.md`; topic -> `.echo/research/<slug>.md`).
2. Spawn the `researcher` subagent (Task tool) with this instruction: "Load the
   `echo:research-template` skill. Research the question and write the grounded result to
   <the path from step 1>. Put a source on every claim (file:line, a URL you fetched, a
   command you ran, or a named system); label inference as inference; never fabricate. Write
   only that one file under `.echo/`; make no code edits." Pass along the full question: $ARGUMENTS
3. Confirm the file was written and show me where it is. This does not change the stage or any
   gate; research is supplementary. When I am ready to start work, `/echo:intent <TICKET> ...`
   will read this research doc and ground the intent in it.
