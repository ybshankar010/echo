---
description: Run the repo's tests/checks (Test stage) and record a proof artifact
argument-hint: [-- <explicit command>]
---

Verify the current work using the `verifier` subagent, then record proof.

1. Spawn the `verifier` subagent (Task tool) with this instruction: "Run the
   project's checks and report only. If a command was provided after `--`, run
   exactly that; otherwise auto-detect the stack. Report the exact commands, pass or
   fail, and the output tail. Do not edit any files." Pass along: $ARGUMENTS
2. Regardless of the subagent, record a durable proof artifact by running:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-verify" $ARGUMENTS
   ```
   This writes `.echo/verify/<ticket>.md` with the real exit code.
3. Report PASS/FAIL to me. If it passed and we are at the test stage, tell me I can
   `/echo:approve` and `/echo:next` toward Ship. If it failed, summarize what broke;
   the hard Stop gate will keep the session from ending until it is green.
