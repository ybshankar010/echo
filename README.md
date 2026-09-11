# echo

A personal, AI-native SDLC plugin for Claude Code. It drives one work item through
**Plan -> Design -> Build -> Test -> Ship** as version-controlled markdown artifacts,
with an explicit human gate at each boundary, deterministic guardrails, file-based
memory that survives session restarts, and a git/PR flow that enforces the organization
Jira ticket policy.

Built by following the [AI-native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook)
on itself — see `.echo/artifacts/{intent,spec,plan}.md`.

## One command (optional)
```
/echo:flow FEAT-1234 <goal>              # drive the whole loop; stops only at plan + ship
```
`/echo:flow` runs every mechanical step and auto-approves a stage when its checker/verify is
clean, pausing only at the gates your `autonomy` setting keeps. It is re-runnable: approve a
gate, run it again, it continues. The stage-by-stage commands below still work on their own.

## The loop
```
/echo:research <topic|ticket> <q>        # optional: grounded research.md before work
/echo:intent FEAT-1234 <what you want>   # write intent.md   (Plan)
/echo:approve  ->  /echo:next            # -> spec.md         (Design)
/echo:approve  ->  /echo:next            # -> plan.md         (Build kickoff)
/echo:approve  ->  /echo:next            # code unlocked      (Build)
/echo:build                              # builder subagent implements the plan (Build)
/echo:verify                             # record proof       (Test)
/echo:approve  ->  /echo:next
/echo:ship  -m "..."                     # branch/commit/rebase/push/PR (Ship)
/echo:watch                              # monitor the PR's CI + reviews (post-ship)
```
`/echo:status` tells you where you are at any time.

## What's inside
- **Commands** (`/echo:*`): flow, research, status, intent, approve, next, spec, plan, build,
  verify, review, ship, watch, install-hooks.
- **Orchestrator**: `/echo:flow <ticket> <goal>` drives the loop from one goal, auto-approving
  stages whose check is clean and stopping only at the gates your `autonomy` setting keeps.
  A failed check always stops. It never adds a gate; it just automates the mechanical steps.
- **Subagents**: `researcher` (grounded research before work), `builder` (implements the
  approved plan), `critic` (checks plan.md against spec.md), `verifier` (runs tests, reports),
  `reviewer` (applies `REVIEW.md`).
- **Research (optional, pre-intent)**: `/echo:research <topic|ticket> <question>` spawns the
  `researcher` to write a grounded `research.md` (a source on every claim). Topic-first docs
  land in `.echo/research/<slug>.md`, ticket-scoped ones in `.echo/artifacts/<ticket>/research.md`;
  `/echo:intent` reads it if present. It changes no stage or gate.
- **Maker-checker loop**: at the Plan and Build stages a maker produces and a checker
  critiques, bounded by an iteration cap, so accuracy is raised before the human gate.
  `/echo:build` runs `builder` + `reviewer`; `/echo:plan` runs the generator + `critic`.
  `/echo:approve` also runs the stage's checker and flags issues before you confirm.
- **Hooks**: SessionStart/PostCompact recall; a hard Stop **verification gate**; a
  Stop capture of recap + episodes; a PreToolUse **plan-guard** (no code before an
  approved plan); plus an installable `commit-msg` ticket gate.
- **Jira progress comments**: as `/echo:flow` completes each stage (and stops at a gate) and
  `/echo:ship` opens a PR, echo posts one concise progress comment to the work item's Jira ticket
  via the Atlassian MCP (`addCommentToJiraIssue`): a headline plus a brief phase summary, with a
  gate stop noting "awaiting your review" and ship posting the PR link. A deterministic gate in
  `bin/echo-stage` (`comment-needed` / `comment-done`, backed by a per-ticket ledger under
  `.echo/jira/`) decides whether a comment is due and records it, so nothing is duplicated. It
  fails open: no ticket, no MCP, or a post error leaves the loop unchanged and posts nothing, and
  echo never changes the Jira status field.
- **Post-ship watch (mandatory)**: after `/echo:ship` opens a PR, `/echo:watch` (also run by
  `/echo:ship` and `/echo:flow`) runs `bin/echo-watch`, which polls the PR's CI checks to a
  resolved state (a short bounded poll, not a daemon), reads its review comments (highlighting
  the configured `review_bot_login`), and writes `.echo/verify/<ticket>-ci.md`. It posts at most
  one Jira comment per distinct event (CI failed on a head sha, a new targeted review comment),
  deduped by the same per-ticket ledger. It fails open: no `gh`/auth/remote/PR records
  `skipped: <reason>` and posts nothing. The step is enforced in code: `echo-stage next` refuses
  to advance `ship -> done` unless a watch artifact exists (governed by `watch_gate`).
- **State** (committed in `.echo/`): `state.json`, `config.json`, `artifacts/`,
  `verify/`, `review/`, `research/`, `jira/`, `recap.md`, `episodes.jsonl`.

## Configuration — `.echo/config.json`
```json
{
  "jira_required": true,
  "plan_guard": "deny",
  "plan_guard_override": false,
  "base_branch": "develop",
  "verify_gate": "block",
  "watch_gate": "block",
  "review_bot_login": "",
  "build_driver": "subagent",
  "maker_checker": "on",
  "maker_checker_max_iters": 2,
  "approve_review": "flag",
  "autonomy": "checkpoint"
}
```
- `plan_guard`: `deny` | `warn` | `off`. Escape hatch: `plan_guard_override: true`.
- `verify_gate`: `block` (hard) | `warn`.
- `watch_gate`: `block` (default; `echo-stage next` refuses `ship -> done` without a post-ship
  watch artifact) | `warn` (advance with a notice) | `off` (disable the check).
- `review_bot_login`: GitHub login whose PR review comments trigger a Jira alert and are labeled
  "Claude review" in the watch artifact. Empty (default) lists all comments but posts none.
- `build_driver`: `subagent` (the `builder` implements the plan) | `manual` (you do).
- `maker_checker`: `on` | `off`. Runs the Plan/Build checker loop.
- `autonomy`: how many gates `/echo:flow` stops at. `gated` (every stage) |
  `checkpoint` (only `plan` + `ship`, the default) | `auto` (only `ship`, plus any failure).
- `maker_checker_max_iters`: how many maker revisions the loop allows (default 2).
- `approve_review`: `flag` (run the checker on approve and warn) | `off`.

## Scope
v1 targets the solo-developer loop. Out of scope (future): managed enterprise
settings, security scans, org marketplace distribution, DORA dashboards, and the
Maintain-stage control bands.

See `INSTALL.md` to install locally. Requires Python 3 and (for Ship) `git` + `gh`.
