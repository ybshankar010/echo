# Intent: Mandatory post-ship CI and review monitoring

- **Ticket:** FEAT-6833
- **Stage:** Plan
- **Author:** echo-contributor
- **Status:** draft (awaiting `/echo:approve`)

## Problem
`/echo:ship` ends the moment the PR is opened. `bin/echo-git` runs
branch/commit/rebase/push/`gh pr create`, posts a best-effort Jira comment with the PR link,
and returns; it never polls CI or reads review comments after that
(research: `.echo/research/post-ship-ci-and-review-monitoring.md`, Finding 1, citing
`bin/echo-git:122-127`). So the loop declares ship done while the PR's CI may still be running
or failing, and any Claude review comments left on the PR go unseen unless the developer
watches GitHub by hand. A repo-wide grep for `watch|monitor|subtask|post-ship` returns zero
hits: this capability does not exist today (research Finding 3).

## Proposed outcome
After `/echo:ship` opens the PR, echo runs a post-ship monitoring step that watches the PR's
CI to a resolved state and surfaces review comments (targeting Claude-authored ones; see Open
questions on how a Claude comment is identified), then reports pass or fail. This step is
**mandatory**, not optional. That word must mean code-enforced, not prose: today every real gate
in echo blocks in code (`echo-plan-guard` and `echo-verify-gate` exit 2), while the Jira-comment
steps are explicitly best-effort/fail-open (`commands/flow.md`, `commands/ship.md`), i.e. soft.
The leaning (settled in spec) is a code-level check, mirroring the verify-gate pattern, that
refuses to advance `ship -> done` unless a watch artifact was recorded, so a bare `/echo:ship`
or a skipped flow step cannot ship past monitoring. It is delivered as the research's recommended
Option 2 (research "Recommendation"): a standalone stdlib `bin/echo-watch` CLI plus a
`/echo:watch` command, with no new entry added to `STAGES`. On a CI failure or a new targeted
review comment it posts one concise Jira comment, reusing the existing ledger so it never
double-posts. It fails open on infrastructure gaps: missing/unauthenticated `gh`, no PR, or an
API error leaves the loop unchanged and never fabricates a status (this is distinct from the
mandatory gate above, which blocks only when a watch was genuinely never run).

## Affected users / systems
- **Developer** running `/echo:flow` / `/echo:ship`: now gets an automatic post-ship CI and
  review check instead of a manual GitHub watch.
- **echo internals:** new `bin/echo-watch` and `commands/watch.md`; edits to `commands/ship.md`
  and `commands/flow.md` to invoke it as a required step; reuse of `lib/echo_common.py` helpers
  (`verify_dir`/`review_dir` for the artifact, the `comment-needed`/`comment-done` ledger at
  `lib/echo_common.py:213-231`). No change to `STAGES` or the state schema (research Finding 2,
  Option 2).
- **External:** `gh` CLI (2.91.0, research Finding 4) and the target GitHub repo's PR checks and
  review comments; the work item's Jira ticket via the Atlassian MCP (comment only, status
  field never touched).

## Constraints
- Stdlib Python only, no third-party dependency, matching `echo-git`/`echo-stage`
  (`CLAUDE.md` Conventions; research Finding 7).
- Do not add a new `STAGES` entry and do not rely solely on a Stop hook (research rejects
  Options 1 and 3): the ship -> done model stays, monitoring lives in the ship/flow orchestration.
- Fail open everywhere: no `gh`/auth, no PR, or an API error must exit cleanly and never block
  or fabricate. Never post to Jira without a valid ticket; never change Jira status.
- "Continuous" is a **bounded** wait, not a daemon: there is no timer/cron/webhook substrate in
  this repo (research Finding 6 and Risks). The watch is a bounded poll (or an explicit blocking
  `gh pr checks --watch`) with a cap, honest about that limit.
- No secrets, tokens, diffs, or file contents in Jira comments.
- Non-goals: a background daemon or scheduler; non-GitHub CI systems; configuring or installing
  the Claude review bot itself (that is GitHub/org config, research Finding 5); auto-merging or
  reacting to review comments beyond surfacing them.

## Open questions
- **CI field:** use `gh pr checks --json bucket,name,state,link` or `gh pr view --json
  statusCheckRollup`? Research flagged `statusCheckRollup` as not directly confirmed on this `gh`
  (Risks). Leaning: `gh pr checks --json` as the primary (its "exit 8 = pending" is documented,
  Finding 4), verify `statusCheckRollup` in spec before choosing.
- **Review-comment read path:** plain `gh api repos/{owner}/{repo}/pulls/{n}/comments` vs. the
  GitHub MCP. The exact MCP read-tool name was unverified in research (Finding 5); the session
  does expose `mcp__claude_ai_github-custom__pull_request_read`. Leaning: shell out to `gh api`
  as the primary (keeps `bin/echo-watch` self-contained and stdlib), document the MCP as fallback.
- **Identifying a Claude comment (was unresolved in research Finding 5 and Risks):** which GitHub
  login does the Claude review bot post under, and is one even installed on the target repo? This
  is GitHub/org config, outside echo, and unconfirmed. Leaning: make the matched author a
  configurable value (e.g. an `echo` config key or `--author` flag, default a documented bot
  login pattern), surface all review comments when unset, and fail open (surface nothing, do not
  error) when the repo has no such bot. Must be settled in spec before build; without it the
  feature either matches a wrong login and silently finds nothing, or floods Jira with every
  reviewer's comment.
- **Mandatory enforcement (code, not prose):** does `/echo:ship` run the watch right after PR
  creation, and does `/echo:flow` refuse `ship -> done` without a watch artifact, and is that
  refusal enforced in a `bin/` check (e.g. `echo-stage next` or a gate) rather than only in
  command markdown? Leaning: yes to all, mirroring `echo-verify-gate`'s exit-2 pattern, so
  "mandatory" holds even outside `/echo:flow`. Exact enforcement point to be chosen in spec.
- **Blocking vs. bounded poll default:** default to a bounded poll with a time cap, with
  `--watch` for an explicit blocking wait? Leaning: yes, bounded poll by default so an agent turn
  is never stalled indefinitely (research Finding 4 blocking caveat).
- **Duplicate-comment keys:** the ledger records "posted once ever" per event name
  (`lib/echo_common.py:219-231`); reuse needs distinct keys (e.g. `ci:failed`, `review:seen:<id>`)
  so a new failure or a new comment can re-alert without spamming (research Risks). Exact keys to
  be settled in spec.

## How we know it worked
- After a ship in a real git+PR context, `/echo:flow` runs `echo-watch` automatically and writes
  a monitoring artifact under `.echo/` (e.g. `.echo/verify/<ticket>-ci.md`) recording CI result
  and the targeted review comments.
- The advance from `ship` to `done` is refused (in code) when no watch artifact was recorded,
  proving the step is mandatory rather than best-effort.
- On a failing check, exactly one `ci:failed` Jira comment is posted; re-running `echo-watch`
  while still failing posts nothing new (ledger holds).
- With no `gh`/auth or no PR, `echo-watch` exits 0, posts nothing, and the loop is unchanged.
- Unit tests and `tests/smoke.sh` cover the new command and stay green. The watch's live `gh
  pr checks`/`gh api` paths need mocking or a fixture in tests (not a 1:1 port of `ship
  --dry-run`, which only prints local commands); the smoke line covers the fail-open no-PR path.
