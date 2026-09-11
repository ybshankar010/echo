# Plan: Mandatory post-ship CI and review monitoring

- **Ticket:** FEAT-6833
- **Stage:** Build (kickoff)
- **Derived from:** `.echo/artifacts/FEAT-6833/spec.md`
- **Status:** draft (awaiting `/echo:approve`)

## Files that change
- **`lib/echo_common.py`** (edit) — add two `DEFAULT_CONFIG` keys: `watch_gate: "block"` and
  `review_bot_login: ""`. Add `watch_artifact_relpath(ticket)` and `watch_artifact_path(ticket,
  root=None)` returning `.echo/verify/<ticket>-ci.md` (reusing `verify_dir()`), mirroring the
  `artifact_relpath`/`artifact_path` shape. Add a **pure** helper `parse_checks(data: list) ->
  (result, failing_names)` that maps a parsed `gh pr checks --json bucket,state,name,link` list to
  `("pass"|"fail"|"pending", [names])` (pending if any bucket is `pending`, fail if any is `fail`,
  else pass; empty list -> `pending`). Pure and importable so it is unit-tested directly like
  `slugify`/`load_config` (no network, no subprocess) - this is what `echo-watch` calls. No
  schema/`STAGES` change.
- **`bin/echo-watch`** (new, executable `100755`, `#!/usr/bin/env python3`, stdlib only, imports
  `echo_common as ec` via the same `sys.path.insert` prologue as `bin/echo-stage`) — the
  determinism layer: resolve the PR, poll CI, read review comments, write the artifact, and print
  the due Jira events. Never calls the MCP (that stays in the command layer, matching how
  `comment-needed`/`comment-done` split from the markdown post).
- **`bin/echo-stage`** (edit `cmd_next`) — enforce the mandatory watch gate on the `ship -> done`
  advance.
- **`commands/watch.md`** (new) — `/echo:watch`: runs `echo-watch run`, posts the due Jira events
  via `addCommentToJiraIssue`, records each with `echo-stage comment-done`, prints the artifact.
- **`commands/ship.md`** (edit) — after the PR is opened (new step 6), run `echo-watch run` and
  surface its result, so a bare `/echo:ship` also triggers monitoring.
- **`commands/flow.md`** (edit) — after the ship gate is approved and `/echo:ship` has run, run the
  watch (if no artifact yet) before the `ship -> done` advance, so the orchestrator enforces it too.
- **`README.md`** (edit) — document the mandatory post-ship watch, `/echo:watch`, `watch_gate`, and
  `review_bot_login`.
- **`tests/test_echo.py`** (edit) — add unit tests (below).
- **`tests/smoke.sh`** (edit) — add a fail-open no-PR line.

## `bin/echo-watch` interface (build to this)
- `checks --ticket T [--json] [--interval 15] [--max-wait 120] [--watch]` — resolve PR via
  `gh pr view --json number,url` (cwd = `ec.repo_root()`); poll `gh pr checks <n> --json
  bucket,state,name,link` every `interval`s, passing each parsed result through
  `ec.parse_checks(...)`, until it is not `pending` or `max-wait` elapses (`--watch` instead execs
  `gh pr checks <n> --watch --fail-fast`). Print a summary (or JSON with `--json`). Exit non-zero
  and list failing check names when CI failed; exit 0 on pass/pending.
- `comments --ticket T [--author LOGIN] [--since ISO] [--json]` — `gh api
  repos/{owner}/{repo}/pulls/<n>/comments` (the `{owner}/{repo}` placeholders auto-resolve from
  `origin`); merge `gh pr view --json comments,latestReviews`. `--author` (else config
  `review_bot_login`) marks matched comments as "Claude review"; unset lists all but marks none.
- **Invariant:** `run` is always invoked for the currently-active / just-shipped ticket, so the
  posting side (`echo-stage comment-done --event <key>`, which records under the *active* ticket's
  ledger per `cmd_comment_done`) and `echo-watch`'s `--ticket T` are the same ticket. `commands/
  watch.md` must pass the active ticket as `--ticket`; do not run `echo-watch run --ticket X` while
  a different ticket is active (it would record dedup keys under the wrong ledger).
- `run --ticket T` — the mandatory entry: (1) write the artifact FIRST as `result: started`
  (`ec.watch_artifact_path`); (2) fail open — if `gh` missing, `gh auth status` non-zero, no
  remote, or no open PR, rewrite the artifact `result: skipped` + `- reason:` and exit 0; (3) run
  the bounded `checks` then `comments`; (4) rewrite the artifact with `result: pass|fail|pending`,
  failing check names, PR url, and the review comments (author, one-line body, html_url) - never
  any diff, token, or secret; (5) load `ec.load_jira_ledger(T)` and for each event not present,
  print one line `post <event-key>\t<summary>`: `ci:failed:<head-sha>` when CI failed, and
  `review:seen:<comment-id>` per new targeted comment. Always exit 0 (orchestration reads the
  artifact, not the code).
- Head sha for the CI key: `gh pr view --json headRefOid` (fallback `ec.git("rev-parse","HEAD")`).

## `cmd_next` gate (build to this)
In `bin/echo-stage:cmd_next`, after the existing "gate approved" check and computing `nxt`, before
`item["stage"] = nxt`:
```
if stage == "ship" and nxt == "done":
    mode = ec.load_config().get("watch_gate", "block")
    if mode != "off" and not os.path.exists(ec.watch_artifact_path(ticket)):
        if mode == "block":
            print("echo: cannot advance ship -> done - no post-ship watch recorded. "
                  "Run `/echo:watch` (or `echo-watch run`) first.", file=sys.stderr)
            sys.exit(2)
        print("echo: warning - advancing ship -> done without a watch artifact.", file=sys.stderr)
```
Fail open: the guard only runs when there is an active item (already guaranteed above); an
unmappable item never reaches here, matching every other echo gate.

## Order of work
1. `lib/echo_common.py`: config keys + `watch_artifact_relpath`/`watch_artifact_path`. (Foundation.)
2. `bin/echo-watch`: implement the three subcommands; `chmod +x`. (Depends on 1.)
3. `bin/echo-stage` `cmd_next`: add the watch gate. (Depends on 1; disjoint file from 2, parallel-ok.)
4. `commands/watch.md`, and edits to `commands/ship.md` + `commands/flow.md`. (Prose; parallel with 2-3.)
5. `README.md` doc. (Prose; parallel.)
6. `tests/test_echo.py` + `tests/smoke.sh`. (After 1-3.)
7. Run the full Proof below; fix code (not tests) until green.

## Risks
- **A blocking `gh` call stalls the turn.** Mitigation: default is a bounded poll (`--max-wait`
  120s, under the 600s Bash ceiling); `--watch` is opt-in. `run` writes the artifact first so an
  interrupted poll never strands the item at `ship`.
- **Wrong/missing Claude bot login.** Mitigation: `review_bot_login` unset -> list all, post none;
  never guess a login.
- **Jira spam on re-run.** Mitigation: parameterized ledger keys (`ci:failed:<sha>`,
  `review:seen:<id>`); same state posts once, a new sha/id re-alerts.
- **Gate bricks a repo without `gh`/PR.** Mitigation: `run` always writes an artifact (even
  `skipped`), so the existence-based gate passes whenever watch was run; `watch_gate: off` is the
  escape hatch; the gate only fires for an active item.
- **PR has no checks registered yet.** Right after a PR opens `gh pr checks` may report zero
  checks (distinct from the exit-8 pending case). Mitigation: `parse_checks([])` returns `pending`,
  so `run` records `result: pending` and exits 0 (fail-open contract); the user re-runs
  `/echo:watch`.
- **`gh` unauthenticated in CI/tests.** Mitigation: tests never call live `gh`; CI parsing is
  tested by importing and calling `ec.parse_checks(...)` on an in-test JSON list, and the
  gate/skip paths against a temp repo with no remote.

## Proof (runnable; this is what Test runs)
1. Compile: `python3 -m py_compile lib/echo_common.py bin/echo-*` -> exit 0.
2. Executable bit: `test -x bin/echo-watch` -> exit 0.
3. Help: `python3 bin/echo-watch run --help` and `... checks --help` and `... comments --help` ->
   exit 0.
4. Config defaults (new unit test): `ec.load_config(tmp)["watch_gate"] == "block"` and
   `"review_bot_login" in ec.load_config(tmp)`.
5. Watch-artifact path (new unit test): `ec.watch_artifact_path("FEAT-1", root)` ends with
   `.echo/verify/FEAT-1-ci.md`.
6. Fail-open `run` (new unit test, temp repo, no remote): `echo-watch run --ticket FEAT-3816`
   exits 0, `.echo/verify/FEAT-3816-ci.md` exists and contains `result: skipped`, prints no
   `post ` line.
7. Mandatory gate (new unit tests, temp repo via `_init_repo`, `set-stage --stage ship`, then
   `approve`):
   - `watch_gate=block`, no artifact -> `echo-stage next` returns 2, stays at `ship`.
   - artifact present (touch `.echo/verify/<t>-ci.md`) -> `next` returns 0, `advanced:done`.
   - `watch_gate=off` (write config) -> `next` returns 0 even with no artifact.
8. Ledger re-alert (new unit test): with `comment-done --event ci:failed:sha1` recorded,
   `comment-needed --event ci:failed:sha1` -> `skip`, but `--event ci:failed:sha2` -> `post`.
   (Reuses the existing `comment-needed`/`comment-done`; only the key is parameterized.)
9. CI parse (new unit test): call `ec.parse_checks(...)` directly (imported like the other `ec`
   unit tests) on in-test JSON lists and assert: all-pass -> `("pass", [])`; one fail ->
   `("fail", ["<name>"])`; any pending -> `("pending", ...)`; `[]` -> `("pending", [])`. No
   network, no subprocess.
10. Gate fail-open (new unit test): on a temp repo with no echo state, `echo-stage next` exits 2
    via the existing `_require_state` guard (the new watch-gate code is never reached without an
    active item, so it cannot crash) - demonstrates acceptance criterion 5.
11. Full suite: `python3 -m pytest tests/test_echo.py -q` all pass; `bash tests/smoke.sh` prints
    its lines and exits 0 (including the new no-PR fail-open line).

## Definition of done
- All Proof checks pass; existing 45 tests stay green (no test weakened).
- `bin/echo-watch` is committed executable; no third-party import anywhere.
- `echo-stage next` blocks `ship -> done` without a watch artifact under `watch_gate: block`, and
  fails open (no crash) when unmappable or when `gh`/PR is absent.
- `/echo:ship` and `/echo:flow` both invoke the watch as a required step; `/echo:watch` exists.
- README documents the step, `watch_gate`, and `review_bot_login`.
- No secrets/tokens/diffs in any artifact or Jira comment; Jira status never changed.
