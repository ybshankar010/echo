# Plan: Post Jira comments as /echo:flow progresses

- **Ticket:** FEAT-9999
- **Stage:** Build (kickoff)
- **Derived from:** spec.md (approved)
- **Status:** draft (awaiting `/echo:approve`)

## Files that change
- `lib/echo_common.py` - add `jira_dir()` (`.echo/jira`) and include it in `ensure_dirs()`;
  add `jira_ledger_path(ticket)`, `load_jira_ledger(ticket, root=None)` and
  `save_jira_ledger(ticket, data, root=None)` (thin wrappers over `_read_json`/`_write_json`,
  returning `{}` on a missing/corrupt ledger so callers fail open).
- `bin/echo-stage` - add two subcommands: `comment-needed --event <event>` and
  `comment-done --event <event>`, plus their argparse registration in `main()`.
- `commands/flow.md` - after each stage's work completes (auto-advance or gate stop), gate an
  `addCommentToJiraIssue` call through `comment-needed` / `comment-done`.
- `commands/ship.md` - after the PR is opened, post the PR-link comment via the same gate.
- `README.md` - document the Jira progress comments and add `.echo/jira/` to the state list.
- `.claude-plugin/plugin.json` - bump version `0.4.0 -> 0.5.0`.
- `tests/test_echo.py` - unit tests for the ledger helpers and the two subcommands.
- `tests/smoke.sh` - a comment-needed -> comment-done -> comment-needed round trip.

## Order of work
1. `lib/echo_common.py`: add `jira_dir` + `ensure_dirs` entry, and the three ledger helpers.
   Reuse `_read_json`, `_write_json`, `now_iso`, `echo_dir`.
2. `bin/echo-stage`: add `cmd_comment_needed` and `cmd_comment_done` and register them.
   - `comment-needed`: `ticket, item = ec.active_item(ec.load_state())`; if no item or
     `not ec.TICKET_RE.fullmatch(ticket)` -> print `skip`, exit 0. Else load the ledger; if
     `event` in it -> `skip`, else `post <ticket>`. Always exit 0 (fail open).
   - `comment-done`: load the ledger for the active ticket, set `ledger[event] = ec.now_iso()`,
     `save_jira_ledger`. Mkdir handled by `save_jira_ledger` via `ensure_dirs`/`makedirs`.
3. Prose wiring (disjoint files, can run in parallel):
   - `commands/flow.md`: at each stage transition and at a gate stop, run
     `echo-stage comment-needed --event stage:<stage>`; if it prints `post <ticket>`, resolve
     the Atlassian `cloudId` via `getAccessibleAtlassianResources`, build the comment from that
     stage's artifact/check result using the spec templates, call `addCommentToJiraIssue`, then
     `echo-stage comment-done --event stage:<stage>`. Wrap the MCP calls so any failure is
     swallowed and the loop continues (fail open). Two placement details (Requirements 2 and 6):
     the call site is the single point after the automated check and the `gate-mode` decision
     (`commands/flow.md` step 5), which sits OUTSIDE the plan/build maker-checker loops, so no
     comment fires per inner iteration. Use the plain per-stage template when the stage
     auto-advances, and the "awaiting your review" variant when `gate-mode` returned `stop`.
   - `commands/ship.md`: after PR creation, `comment-needed --event ship`; if `post`, comment
     with the PR URL, then `comment-done --event ship`.
4. `README.md` + `plugin.json` version bump.
5. `tests/test_echo.py` + `tests/smoke.sh`; run the full Proof below.

## Risks
- An MCP failure mid-loop blocking a stage - mitigation: the deterministic gate never depends on
  the MCP; the command prose wraps every `addCommentToJiraIssue` call and treats any error as
  skip (Requirement 7). Nothing in `bin/` touches the network.
- Duplicate comments across sessions or on resume - mitigation: the committed per-ticket ledger
  keyed by event; `comment-needed` returns `skip` for an already-posted event.
- Corrupt/missing ledger - mitigation: `load_jira_ledger` returns `{}` on any read error, so at
  worst one event could re-post once; never a crash.
- Ticketless research posting - mitigation: `comment-needed` prints `skip` when the active item
  has no valid `[A-Z]+-[0-9]+` ticket. Covered by a unit test.
- Wrong Atlassian site (cloudId) - mitigation: resolve via `getAccessibleAtlassianResources`;
  if none/ambiguous, fail open (skip).
- Data leakage into Jira (spec Flagged concerns) - mitigation: comments use only the per-stage
  templates (headline plus a brief phase summary); never paste diffs, file contents, secrets,
  or tokens into a comment.

## Proof
- `python3 -m py_compile lib/echo_common.py bin/echo-*` -> exits 0.
- `python3 -m pytest tests/test_echo.py -q` -> all pass, including:
  - `comment-needed --event stage:spec` prints `post FEAT-9999` on a fresh ticketed item;
    prints `skip` after `comment-done --event stage:spec`.
  - `comment-needed` prints `skip` (exit 0) when the active item has no valid ticket.
  - the ledger is per ticket (an event for one ticket does not suppress another).
  - `comment-needed` prints `skip` and exits 0 when there is no state (fail open).
- `bash tests/smoke.sh` -> `ALL SMOKE CHECKS PASSED`, including the comment gate round trip.
- Manual (Atlassian MCP connected, not in CI): `/echo:flow <TICKET> <goal>` posts one comment
  per completed stage and one at the plan gate; a re-run posts no duplicate; `/echo:ship` posts
  the PR URL; disconnecting the MCP leaves the loop unaffected and posts nothing; the Jira status
  field is unchanged.

## Definition of done
- `comment-needed` / `comment-done` implemented and unit-tested (post, skip, dedup, ticketless
  skip, fail open); ledger helpers in `lib/echo_common.py`.
- `commands/flow.md` and `commands/ship.md` post via the MCP, gated by the ledger, failing open.
- No Jira status transitions anywhere; comments only.
- README updated, version bumped to `0.5.0`, and the full Proof above is green (output pasted).
