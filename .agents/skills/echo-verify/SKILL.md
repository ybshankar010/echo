---
name: echo-verify
description: Run the repo's tests/checks (Test stage) via the verifier role and record a proof artifact. Use when a change is built and needs verifying before ship.
---

# echo verify (Codex)

Codex port of echo's `/echo:verify` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any explicit
command (given after `--`) from what the user typed; never fabricate a ticket.

## Steps
1. Delegate in prose to the `verifier` role (`.codex/agents/verifier.toml`): "Run the
   project's checks and report only. If a command was provided after `--`, run exactly that;
   otherwise auto-detect the stack. Report the exact commands, pass or fail, and the output
   tail. Do not edit any files." Pass along any explicit command the user gave.
2. Regardless of the delegated result, record a durable proof artifact by running:
   ```
   python3 bin/echo-verify <any explicit command>
   ```
   This writes `.echo/verify/<ticket>.md` with the real exit code.
3. Report PASS/FAIL. If it passed and we are at the test stage, tell the user they can
   approve and advance toward Ship. If it failed, summarize what broke; the hard Stop gate
   will keep the session from ending until it is green.

## Under Codex
Gates are advisory and orchestration is prose-driven. Where the Claude command spawns the
`verifier` via the Task tool, delegate in prose to `.codex/agents/verifier.toml`. See
`.agents/skills/README.md` for the Known limitations before relying on this.
