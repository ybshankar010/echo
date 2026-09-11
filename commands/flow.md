---
description: Drive the whole echo loop from a single goal, auto-advancing clean stages and stopping only at the gates that matter
argument-hint: <TICKET-ID> <goal>  [--research]
---

Orchestrate the echo SDLC loop end to end for: $ARGUMENTS

This reduces the loop to a few touchpoints: it runs the mechanical work and auto-approves any
stage whose automated check comes back clean, and stops for me only where a human decision
matters. It is re-runnable: it reads `echo-stage status` and continues from wherever the item
is, so after I approve a gate I just run `/echo:flow <TICKET>` again to keep going.

## Setup
1. Extract a Jira ticket id (`[A-Z]+-[0-9]+`) from the arguments. If none is present, STOP and
   ask me for it. Never fabricate one (organization policy).
2. Read `.echo/config.json`. The `autonomy` level decides which gates I stop at:
   - `gated` -> stop at every stage.
   - `checkpoint` (default) -> stop only at `plan` and `ship`.
   - `auto` -> stop only at `ship` (and on any failure).
   You never decide this yourself; ask the bin (`echo-stage gate-mode --stage <stage>`) per stage.
3. If `--research` was passed, run the `/echo:research <TICKET> <goal>` flow first so the intent
   can cite it.
4. If there is no active item yet (or it is a different ticket), run the `/echo:intent <TICKET>
   <goal>` flow to initialize and write `.echo/artifacts/<TICKET>/intent.md` (citing any research).

## Drive loop
Repeat until the item reaches `done` or you hit a stop:

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status` to see the current stage and gate.
2. If the current stage's artifact/action is not done yet, produce it with the existing flow:
   - `spec`  -> the `/echo:spec` flow (spec-template skill; write `.echo/artifacts/<TICKET>/spec.md`).
   - `plan`  -> the `/echo:plan` flow, including its `critic` maker-checker loop.
   - `build` -> the `/echo:build` flow (the `builder` + `reviewer` maker-checker loop).
   - `test`  -> the `/echo:verify` flow (records `.echo/verify/<TICKET>.md`).
   - `ship`  -> handled at the stop below.
3. Run the stage's automated check and read its result:
   - `intent` -> `critic` over intent vs the goal/research.
   - `spec`   -> `critic` over spec vs intent.
   - `plan`   -> the `critic` result from its maker-checker loop.
   - `build`  -> the `reviewer` result from its maker-checker loop.
   - `test`   -> the `echo-verify` exit code.
4. If the check FAILED (important/blocking findings, or verify non-zero): STOP. Summarize what
   failed, do NOT approve, and tell me how to fix or override. A failed check always stops,
   whatever the autonomy level.
5. Otherwise ask the bin whether to pause here:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" gate-mode --stage <current-stage>
   ```
   - `stop` -> post the Jira progress comment for this stage (step 6, gate-stop variant), then
     summarize the artifact and the clean check result and STOP. Tell me to review and
     `/echo:approve`, and that `/echo:flow <TICKET>` resumes from here. (At `ship`, do NOT run
     step 6: there is no `stage:ship` comment. The ship comment is posted by `/echo:ship` itself,
     after the PR exists. Once I approve, run the `/echo:ship` flow.) After the ship gate is
     approved and `/echo:ship` has run, and before the `ship -> done` advance, run the mandatory
     post-ship watch if no artifact exists yet (`.echo/verify/<TICKET>-ci.md`): run
     `python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-watch" run --ticket <TICKET>` (it fails open and
     always writes the artifact) and post any `post <event-key>` lines as `/echo:watch` step 3
     does. This is required: `echo-stage next` blocks `ship -> done` under `watch_gate: block`
     until the watch artifact exists.
   - `auto` -> post the Jira progress comment for this stage (step 6, plain variant), then
     approve and advance without me:
     ```
     python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" approve
     python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" next
     ```
     Then continue the loop.
6. Post the Jira progress comment for the stage you just cleared. This is the single call site,
   OUTSIDE the plan/build maker-checker loops, so no comment fires per inner iteration. It is
   best-effort: any failure is swallowed and the loop continues unchanged (fail open). echo never
   changes the Jira status field and never posts without a valid ticket.
   Skip this step entirely when the current stage is `ship`: the only events are
   `stage:intent`, `stage:spec`, `stage:plan`, `stage:build`, `stage:test`; the `ship` comment
   (with the PR link) is posted by `/echo:ship` after the PR is opened, not here.
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" comment-needed --event stage:<current-stage>
   ```
   - If it prints `skip` (no ticket, no active item, or already posted) -> post nothing; continue.
   - If it prints `post <ticket>` -> resolve the Atlassian `cloudId` via
     `getAccessibleAtlassianResources` (if it cannot be resolved or is ambiguous, treat as skip
     and post nothing), then call `addCommentToJiraIssue` with that `cloudId` and the resolved
     ticket key as `issueIdOrKey`. Build the comment from this stage's real artifact or check
     result using the template below (headline plus a brief one-line statement). Never paste
     diffs, file contents, secrets, or tokens. On the plain (auto-advance) path use the template
     as-is; on the gate-stop path append " awaiting your review". If the MCP call errors, swallow
     it and continue. Only after a successful post, record it:
     ```
     python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" comment-done --event stage:<current-stage>
     ```
   Per-stage templates (headline + brief statement grounded in the real artifact):
   - intent: "echo: intent captured." + the problem/outcome in one sentence.
   - spec:   "echo: spec drafted." + the key requirements or decisions.
   - plan:   "echo: plan ready for review." + the approach / files that change.
   - build:  "echo: build complete, review clean." + what changed.
   - test:   "echo: verified green." + the checks that ran.

## On every stop
State plainly: the ticket, the stage we stopped at, why (a gate or a failure), what to review,
and the single command to resume (`/echo:flow <TICKET>`). Do not auto-approve a stop gate, and
do not weaken any check to keep moving. Ship policy is unchanged: `/echo:ship` still enforces the
ticket id and the Co-Authored-By trailer.
