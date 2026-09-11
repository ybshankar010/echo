# Spec: Mandatory post-ship CI and review monitoring

- **Ticket:** FEAT-6833
- **Stage:** Design
- **Derived from:** `.echo/artifacts/FEAT-6833/intent.md`
- **Status:** draft (awaiting `/echo:approve`)

## Overview
Add a post-ship monitoring step to echo: after `/echo:ship` opens a PR, a new stdlib CLI
`bin/echo-watch` polls the PR's CI checks to a resolved state and reads its review comments
(highlighting a configured Claude bot author), writes a monitoring artifact, and posts at most
one Jira comment per distinct event (CI failed, new targeted review comment). It is delivered as
research Option 2 (a `bin/` determinism script plus a `commands/watch.md` orchestration file,
matching the `echo-verify` + `/echo:verify` pattern), with no new `STAGES` entry. The step is
made **mandatory in code**: `echo-stage next` refuses to advance `ship -> done` unless a watch
artifact was recorded, mirroring the existing `echo-verify-gate` exit-2 gate. `echo-watch` itself
fails open (missing `gh`/auth/PR never errors) but always writes an artifact so the gate can tell
"ran and skipped for a real reason" from "never ran".

## Requirements
Each is testable and traces to the intent.

1. **New CLI `bin/echo-watch`** (executable, `#!/usr/bin/env python3`, stdlib only, imports
   `echo_common as ec`), with subcommands:
   - `checks --ticket <T> [--json] [--watch] [--interval <s>] [--max-wait <s>]` — reports CI state.
   - `comments --ticket <T> [--since <iso>] [--author <login>] [--json]` — reports review comments.
   - `run --ticket <T>` — the mandatory post-ship entry: runs checks (bounded) then comments,
     writes the artifact, posts due Jira comments. This is what `/echo:ship` and `/echo:flow` call.
   (Intent: "standalone stdlib `bin/echo-watch` CLI".)
2. **CI read path.** `checks` shells out to `gh pr checks <pr> --json bucket,state,name,link`
   (fields confirmed via `gh pr checks --json`). Exit code 8 = pending (documented). Default mode
   is a **short bounded poll**: re-poll every `--interval` (default 15s) until all checks leave the
   pending bucket or `--max-wait` (default 120s) elapses, then record the current result (which may
   be `pending`). `--watch` may instead delegate to the blocking `gh pr checks --watch --fail-fast`
   for a deliberate long wait. The default max-wait is kept well under the calling harness's Bash
   timeout ceiling (600s) so a synchronous `run` from `/echo:ship` is never killed mid-poll; longer
   CI is handled by re-running `/echo:watch` (or `--watch` out-of-band), not by a longer default.
   It must never block unbounded. (Intent: bounded, not a daemon; resolves critic timeout concern.)
3. **Review-comment read path.** `comments` uses `gh api repos/{owner}/{repo}/pulls/{n}/comments`
   (REST review comments) as primary; `gh pr view --json comments,latestReviews` supplements
   conversation-level and formal reviews. The GitHub MCP `pull_request_read` is documented as a
   fallback but the shipped script shells out to `gh` only (self-contained, stdlib). (Intent open
   question "Review-comment read path", resolved to `gh api` primary.)
4. **Claude-author identification.** The author to highlight is configurable: `--author <login>`,
   else `.echo/config.json` key `review_bot_login`, else unset. When set, only comments by that
   login drive a Jira post and are labeled "Claude review" in the artifact; all comments are still
   listed in the artifact. When unset, the artifact lists all review comments and **no**
   author-triggered Jira comment is posted (avoids matching a wrong login or flooding Jira).
   (Intent open question "Identifying a Claude comment", resolved: configurable, fail open.)
5. **Artifact always written, and written first.** `run` writes `.echo/verify/<ticket>-ci.md` via
   a new `ec.watch_artifact(ticket)` helper (reusing `verify_dir()` at `lib/echo_common.py:126-131`)
   BEFORE the poll begins (status `started`/`pending`), then updates it in place with the final
   result. Writing first guarantees the artifact exists even if the calling turn is killed mid-poll,
   so the mandatory gate (req 6) can never strand an item at `ship` merely because a poll was
   interrupted. The artifact records: timestamp, PR number/url (or "none"), CI result
   (`pass`/`fail`/`pending`/`skipped`), failing check names, and the review comments found (author +
   short body + html_url). On fail-open paths it records `skipped: <reason>` and exits 0.
   (Intent: "writes a monitoring artifact under `.echo/`".)
6. **Mandatory gate (code-enforced at the advance).** `echo-stage next` refuses to advance an item
   from `ship` to `done` unless a watch artifact exists for that ticket, governed by a new config
   key `watch_gate` (`block` default | `warn` | `off`). `block` prints how to run `/echo:watch` and
   exits non-zero without advancing; `warn` advances with a notice; `off` disables the check. The
   gate FAILS OPEN when it cannot map an active item (never bricks a repo), per `CLAUDE.md`
   Conventions. Scope note (correcting an earlier overclaim): this is enforced at the `ship -> done`
   advance inside `echo-stage next`, NOT as a Stop hook. Unlike `echo-verify-gate` (a SessionStop
   hook wired in `hooks/hooks.json` that blocks the session from ending), this gate does not stop a
   session from ending at `ship`; it blocks completing the loop. That is sufficient for "mandatory"
   because an item cannot reach `done` without a recorded watch. A SessionStop-hook analog
   (`echo-watch-gate`) for true session-level parity is a deliberate NON-goal for this ticket (see
   Non-goals); it can be added later if session-level blocking is wanted. It reuses `verify_gate`'s
   style (fail-open, config-gated, exit non-zero) but not its hook mechanism. (Intent: "code-level
   check ... refuses `ship -> done`".)
7. **Jira comments, ledger-deduped with per-occurrence keys.** Reuse the existing ledger
   (`comment-needed`/`comment-done`, `lib/echo_common.py:213-231`) but with **parameterized** event
   keys so a genuinely new event still alerts while the same event never double-posts:
   - Review comments: one post per comment, keyed `review:seen:<comment-id>` (the GitHub review
     comment id). A second, different comment (different id) alerts; the same id never re-posts.
   - CI failure: keyed by the failing head commit sha, `ci:failed:<head-sha>`, so a fresh failure on
     a new commit re-alerts, but repeated `run`s over the same failing sha post once. (A prior pass
     then a new failure on a new sha is naturally a new key.)
   This directly resolves the intent's "Duplicate-comment keys" open question (flat `ci:failed` /
   `review:new` keys were rejected by review because "posted once ever" semantics would silence
   every later distinct event). Best-effort: any MCP error is swallowed; never post without a valid
   ticket; never touch Jira status. (Intent: "reusing the existing ledger so it never double-posts".)
8. **`/echo:ship` invokes the watch.** After a successful real ship (PR opened), `commands/ship.md`
   runs `echo-watch run --ticket <T>` before telling the user to `/echo:approve` ship. (Intent:
   "`/echo:ship` invokes it once the PR exists".)
9. **`/echo:flow` invokes the watch.** After the ship gate is approved and `/echo:ship` has run,
   `/echo:flow` runs `echo-watch run` (if not already recorded) before the ship->done advance, so
   the mandatory step holds inside the orchestrator too. (Intent: "`/echo:flow` always runs it".)
10. **New command `commands/watch.md`** (`/echo:watch`) orchestrates `echo-watch run` and prints
    the artifact location, matching the thin-orchestration style of `commands/verify.md`.
11. **Fail open on infrastructure.** No `gh` binary, `gh auth status` failing, no git remote, or
    no open PR for the branch: `echo-watch` records `skipped: <reason>`, posts nothing, exits 0.
    (Intent: "fails open ... never fabricates a status".)

## Design
- **Components:** `bin/echo-watch` (new), `commands/watch.md` (new); edits to `commands/ship.md`,
  `commands/flow.md`, `bin/echo-stage` (the `next` gate), `lib/echo_common.py` (helpers + config
  defaults), `README.md` (document the step), `tests/test_echo.py` + `tests/smoke.sh` (coverage).
- **State/artifact:** `.echo/verify/<ticket>-ci.md` (reuses `verify_dir()`); no schema/`STAGES`
  change (research Option 2). Ledger events extended with `ci:failed`, `review:new` keys in the
  existing `.echo/jira/<ticket>.json`.
- **Config:** add `watch_gate: "block"` and optional `review_bot_login` to config defaults in
  `lib/echo_common.py` (wherever `verify_gate`/`base_branch` defaults live), so existing repos get
  the gate on by default but can set `warn`/`off`.
- **PR resolution:** get the PR number/url for the current branch via `gh pr view --json
  number,url`. For the review-comments endpoint, use `gh api`'s `{owner}/{repo}` placeholders,
  which auto-resolve from the current repo's `origin` context (confirmed in `gh api --help`), rather
  than passing head-repo fields (which name the source/fork repo, not the base repo hosting the
  PR). If no PR/remote, fail open (req 11).
- **Key decisions (resolving intent open questions):**
  - CI field: `gh pr checks --json` (confirmed fields `bucket,state,name,link`; documented exit
    8 = pending). `statusCheckRollup` is also a valid `gh pr view --json` field (verified on gh
    2.91.0) but `gh pr checks` is chosen for its explicit pending exit code; statusCheckRollup is a
    future enrichment, not a blocker.
  - Read path: `gh api` primary, MCP `pull_request_read` documented fallback only.
  - Claude author: configurable, unset means list-all-but-do-not-post (honest, no wrong-login risk).
  - Mandatory: enforced at the `ship -> done` advance in `echo-stage next` via `watch_gate`,
    artifact-existence based (artifact written first, req 5), so fail-open watch and the mandatory
    gate coexist without contradiction. Not a Stop hook (see req 6 scope note).
  - Blocking vs bounded: short bounded poll default (`--max-wait` 120s, under the harness ceiling);
    `--watch` is opt-in blocking.

## Flagged concerns
- **Blocking an agent turn (UX):** a naive `--watch` could stall the conversation until CI
  finishes. Mitigation: default is a bounded poll with `--max-wait` (req 2); blocking is opt-in.
- **Jira noise (UX):** re-running the watch could spam comments. Mitigation: ledger dedup on
  distinct event keys (req 7); unset author posts nothing (req 4).
- **Security:** never put diffs, tokens, or secrets in Jira or the artifact; store only comment
  author, short body, and `html_url`. `gh` token stays in `gh`'s keyring; echo never reads it.
- **Compliance:** Jira status field is never changed (echo policy); comments only. No new
  third-party dependency (stdlib rule).
- **Bricking risk:** the new gate must FAIL OPEN when it cannot map the active item, matching every
  other echo gate (`CLAUDE.md`). Owner sign-off not required; this is within existing policy.

## Non-goals
- A background daemon, cron, or webhook receiver (no substrate in-repo; research Finding 6/Risks).
- Non-GitHub CI systems (only `gh`/GitHub investigated).
- Installing or configuring the Claude review bot on the GitHub repo (org config, out of scope).
- Auto-merging, or reacting to/resolving review comments beyond surfacing them.
- Adding a new `STAGES` entry or a new SDLC gate/artifact template (research rejects Option 1).
- A SessionStop-hook analog (`echo-watch-gate`) for session-level blocking (like `echo-verify-gate`)
  is out of scope for this ticket; the `echo-stage next` advance gate (req 6) is the mandatory
  enforcement. A Stop hook can be added later if session-level blocking proves needed.

## Acceptance criteria
1. `python3 -m py_compile lib/echo_common.py bin/echo-*` passes (echo-watch compiles).
2. `bin/echo-watch` is executable (`100755` tracked) and runs `--help` for each subcommand.
3. With no git remote / no PR, `echo-watch run --ticket FEAT-6833` exits 0, writes an artifact
   recording `skipped: <reason>`, and posts nothing (unit test with a temp repo).
4. `echo-stage next` from `ship` with `watch_gate=block` and no watch artifact exits non-zero and
   does not advance; with an artifact present it advances to `done`; with `watch_gate=off` it
   advances regardless (unit tests).
5. The gate FAILS OPEN (advances/no crash) when there is no active item mappable.
6. CI parsing maps `gh pr checks --json` output to pass/fail/pending, listing failing check names
   (unit test against a captured/mocked JSON fixture, not a live call).
7. Ledger dedup with re-alert: two `echo-watch run` calls over the same failing head-sha post
   `ci:failed:<sha>` once; a failure on a NEW head-sha posts again; a NEW review comment id posts a
   `review:seen:<id>` while a repeated id does not (unit tests around `comment-needed`/`comment-done`
   with the parameterized keys, covering both no-double-post and new-event-still-alerts).
8. `tests/smoke.sh` gains a line exercising the fail-open no-PR path end to end; existing smoke
   assertions stay green.
9. `python3 -m pytest tests/test_echo.py -q` and `bash tests/smoke.sh` both pass.
10. `README.md` documents the mandatory post-ship watch, the `watch_gate` config, and `/echo:watch`.
