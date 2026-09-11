# Research: post-ship CI and review-comment monitoring

- **Question:** How can echo add a subtask after ship so that, once the PR is pushed to
  production (opened), it continuously monitors CI status for failures and surfaces Claude
  review comments left on the PR?
- **Date:** 2026-09-11
- **Ticket or Topic:** topic (no Jira ticket given; topic-first research per echo policy)
- **Status:** draft

## Scope
In scope: how `/echo:ship` works today, echo's stage/state model and where a new step would
plug in, echo's hook lifecycle and whether it can drive monitoring, what `gh` and GitHub APIs
offer for CI checks and PR review comments, and 2-3 concrete designs with a recommendation.

Out of scope: implementing the feature, deciding the exact CLI flag names, and any non-GitHub
CI system (only `gh`/GitHub was investigated, per what's installed in this environment).

## Findings

### 1. How ship works today
- `/echo:ship` first requires a fresh passing verify artifact, then runs `bin/echo-git ship`
  as a dry run, shows the plan, and on confirmation runs it for real; it enforces the Jira
  ticket id and Co-Authored-By trailer, rebases onto the base branch, and opens the PR via
  `gh`.
  Source: `commands/ship.md:6-20`
- After a successful ship, the command posts a best-effort Jira comment with the PR link via
  `echo-stage comment-needed --event ship` / `comment-done --event ship`, gated by a per-ticket
  ledger so it never double-posts; failures are swallowed (fail open).
  Source: `commands/ship.md:21-34`; ledger implementation `lib/echo_common.py:213-231`
- `commands/ship.md` ends by telling the user to `/echo:approve` ship and `/echo:next` to
  close the loop. Nothing in `ship.md` mentions CI status or review comments.
  Source: `commands/ship.md:35-36`
- `bin/echo-git` (`cmd_ship`) does: resolve ticket -> checkout/rename branch if on
  base/main/master -> `git add` -> `git commit -m "<ticket>: <message>\n\n<trailer>"` ->
  `git fetch origin` + `git rebase origin/<base>` (pausing on conflict, no auto-resolve) ->
  `git push -u origin <branch>` -> `gh pr create --base <base> --title ... --body ...`. If
  `gh` is missing/unauthenticated (`_has_gh` checks `gh auth status`), it stops after push and
  prints the manual `gh pr create` command.
  Source: `bin/echo-git:58-135` (branch/rename `bin/echo-git:68-75`, commit `bin/echo-git:82-88`,
  rebase `bin/echo-git:90-106`, push `bin/echo-git:108-111`, PR create `bin/echo-git:113-127`,
  `_has_gh` `bin/echo-git:130-135`)
- After `gh pr create`, `echo-git` prints `"echo-git: shipped {ticket} on branch {branch}."` and
  returns; it does not poll checks or fetch reviews after the PR is opened.
  Source: `bin/echo-git:122-127`

### 2. The stage model
- The ordered stage list is `["intent", "spec", "plan", "build", "test", "ship", "done"]`, with
  `GATED_STAGES = STAGES[:-1]` — every stage except `done` has an approval gate. `done` is
  explicitly documented as terminal: "`done` is terminal (no artifact/gate of its own)."
  Source: `lib/echo_common.py:22-24`
- `echo-stage next` advances one stage per call and prints a hint for the newly entered stage;
  the hint table maps `ship -> "Run /echo:ship..."` and `done -> "Loop complete."`. There is no
  stage between `ship` and `done` today, so ship's own gate approval plus one `/echo:next` call
  moves the item straight to the terminal `done` state with no monitoring step in between.
  Source: `bin/echo-stage:105-119` (hints dict), `lib/echo_common.py:254-258` (`next_stage`)
- `.echo/` layout used by the state machine: `state.json` (active ticket + per-ticket
  `stage`/`gates`/`artifacts`), `config.json`, `artifacts/<ticket>/<stage>.md`, `verify/`,
  `review/`, `research/`, `jira/<ticket>.json` (comment ledger), `recap.md`, `episodes.jsonl`.
  Source: `lib/echo_common.py:90-153` (path helpers), `lib/echo_common.py:150-153` (`ensure_dirs`)
- Adding a post-ship step that fits this model means either (a) inserting a new stage name
  into `STAGES` before `done` (a schema/version change touching `GATED_STAGES`, `hints`, and
  every place that iterates `STAGES`), or (b) treating monitoring as a *sub-step inside* the
  existing `ship` stage / a follow-on action taken after `ship`'s gate is approved but before
  `/echo:next` is run, without changing the state machine at all. Inference: (b) is
  structurally cheaper because `STAGES` is a flat list consumed by `GATED_STAGES`,
  `FLOW_STOP_GATES`, `next_stage`, and the `hints` dict in `echo-stage next`
  (`lib/echo_common.py:22-24,44-48`; `bin/echo-stage:111-119`) — inserting a stage means
  updating all of those plus the `/echo:flow` per-stage dispatch table
  (`commands/flow.md:26-31`).

### 3. Hooks model
- The plugin wires five hook events: `SessionStart` and `PostCompact` -> `echo-recall`;
  `PreToolUse` (matcher `Write|Edit|NotebookEdit`) -> `echo-plan-guard`; `Stop` ->
  `echo-verify-gate` then `echo-capture`; `SessionEnd` -> `echo-capture`.
  Source: `hooks/hooks.json:1-41`
- `echo-verify-gate` is a `Stop` hook: it fails open unless the active item's stage is `test`
  or `ship` and `verify_gate == "block"`, in which case it blocks the session from stopping
  (exit 2) until `.echo/verify/<ticket>.md` shows `exit_code: 0`.
  Source: `bin/echo-verify-gate:1-64`
- `echo-capture` (Stop and SessionEnd) writes `.echo/recap.md` and appends one line to
  `.echo/episodes.jsonl` from git state only; it invents nothing and exits 0 always.
  Source: `bin/echo-capture:1-89`
- All of these hooks are **process-lifecycle** events tied to a single Claude Code session
  (session start, tool use, session stop/end) — none of them are a timer or an external
  webhook receiver. There is no hook event in `hooks/hooks.json` that fires on a delay or on
  an external event (e.g., a GitHub webhook, a cron tick) independent of the agent doing
  something in-session. Grep of `commands/`, `bin/`, `lib/`, `skills/`, `agents/`, `templates/`
  for `watch|monitor|subtask|post-ship` returned no matches — this capability does not exist
  in echo today.
  Source: `hooks/hooks.json:1-41`; `grep -rniE "watch|monitor|subtask|post-ship|post ship" commands/ bin/ lib/ skills/ agents/ templates/` (no output)
- Consequence: a Stop hook *could* in principle refuse to let the session end while CI is
  still pending (mirroring `echo-verify-gate`'s pattern), but that only works while the user's
  Claude Code session for that ticket is open — it cannot notify the user hours later after
  the session has ended. Inference, based on the Stop-hook mechanics above.

### 4. CI monitoring mechanics (`gh`)
- `gh` is installed: `gh version 2.91.0 (2026-04-22)`.
  Source: command `gh --version`, output `gh version 2.91.0 (2026-04-22)`
- `gh pr checks --help` confirms both a one-shot and a blocking mode:
  - One-shot: `gh pr checks [<number>|<url>|<branch>]`, with `--json fields` (fields:
    `bucket, completedAt, description, event, link, name, startedAt, state, workflow`) for
    machine-readable output, and documented "Additional exit codes: 8: Checks pending".
  - Blocking: `--watch` ("Watch checks until they finish"), `--interval <seconds>` (default
    10), and `--fail-fast` ("Exit watch mode on first check failure").
  Source: command `gh pr checks --help`
- `gh run watch <run-id>` is a separate blocking command that streams a single workflow run's
  progress live, with `--exit-status` to fail the command if the run fails and `--interval`
  (default 3s). Its help text notes it "does not support authenticating via fine grained PATs".
  Source: command `gh run watch --help`
- `gh pr view --json <fields>` supports a large field list including `statusCheckRollup` (not
  shown in the truncated first page of fields but is a documented field of `gh pr view --json`
  in the GitHub CLI); the fields actually observed in this session's help output include
  `comments`, `commits`, `latestReviews`, `mergeable`, `mergeStateStatus`, among others, up to
  and beyond `headRefName` where output was truncated.
  Source: command `gh pr view --json bogusfield` (error listing valid fields, truncated at
  `headRefName`); Inference: `statusCheckRollup` itself was not directly observed in the
  truncated output and should be re-verified with `gh pr view --json statusCheckRollup` before
  relying on it.
- Distinction that matters for design: `gh pr checks` (no `--watch`) and `gh pr view --json
  statusCheckRollup` are **one-shot polls** — they return immediately with current state and
  are safe to call repeatedly from a script/loop. `gh pr checks --watch` and `gh run watch`
  are **blocking** — they hold the calling process until checks finish, which inside a single
  agent turn would stall the conversation until CI completes (Inference, based on the
  documented behavior of `--watch`/`run watch` above).

### 5. Reading PR review comments (including Claude's)
- GitHub's REST API has a dedicated endpoint for PR review comments:
  `GET /repos/{owner}/{repo}/pulls/{pull_number}/comments`, returning objects with `body`,
  `user.login`, `path`, `line`, `created_at`/`updated_at`, `html_url`, etc. This is reachable
  from this environment via `gh api repos/{owner}/{repo}/pulls/{pull_number}/comments`
  (`gh api` is documented as making "an authenticated HTTP request to the GitHub API").
  Source: https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#list-review-comments-on-a-pull-request (fetched); `gh api --help` output confirming `gh api` proxies REST/GraphQL endpoints
- `gh pr view` also exposes `-c/--comments` ("View pull request comments") and `--json
  comments` / `--json latestReviews` (issue-level comments vs. formal reviews are different
  GitHub objects; `comments` on a PR/issue are the general conversation thread, while
  line-level "review comments" are the `/pulls/{n}/comments` endpoint above). Both were
  observed in the same `gh pr view --help` output.
  Source: command `gh pr view --help`
- A GitHub MCP server is connected in this session ("claude.ai github-custom"), whose own
  instructions (visible in this session's system context) describe tools named by convention
  `list_*` (broad retrieval, e.g., of PRs/issues) and `search_*` (targeted queries), and
  specifically name `pull_request_review_write` and `add_comment_to_pending_review` for
  *writing* reviews. The instructions do not enumerate a specific read tool name (e.g.
  `pull_request_read`) in the text visible to this researcher, so which exact tool returns PR
  review comments is **unverified** — it should be confirmed by listing available MCP tools at
  build time rather than assumed.
  Source: this session's "MCP Server Instructions" system context, "claude.ai github-custom"
  section (named system; exact tool names for reading comments not independently confirmed)
- "Claude review comments" specifically means comments/reviews posted by a Claude-based GitHub
  App/bot account on the PR (e.g., an automated review bot). Nothing in this repo's code
  configures or references such a bot; whether one is installed on the target GitHub repo (and
  under what account/login name its comments would appear) is **unknown and out of scope of
  this codebase** — it is a property of the GitHub repo/org configuration, not of echo.
  Inference, based on no matches for "claude" + "review" wiring anywhere in `bin/`, `lib/`,
  `commands/`, `hooks/` (see the grep in Finding 3).

### 6. Continuous monitoring options actually available in this harness
- Nothing in `hooks/hooks.json` provides a timer/cron/webhook trigger (Finding 3). Any
  "continuous" monitoring must be one of: (a) a blocking `gh ... --watch` call made inside a
  command/agent turn (ties up that turn until it returns), (b) a polling loop written in a
  `bin/echo-*` Python script that sleeps and re-checks up to a bound (still runs synchronously
  inside whatever process invokes it), or (c) a `run_in_background` shell job plus a separate
  mechanism to surface its result later.
  Inference, grounded in Finding 3 (no timer/webhook hook exists) and Finding 4 (gh's own
  one-shot vs. `--watch` split).
- I looked for a `loop` or `schedule` skill inside echo itself (the only skills this plugin
  ships are `intent-template`, `plan-template`, `research-template`, `spec-template`) and
  found none.
  Source: `ls skills/` -> `intent-template  plan-template  research-template  spec-template`
- A filesystem search for `loop`/`schedule` skill files elsewhere on this machine surfaced
  skills belonging to *other, unrelated* plugins and old local-agent-mode session caches
  (e.g., `mattpocock-skills/.../loop-me/SKILL.md`, a `schedule`/`schedule-task` skill under a
  different local-agent-mode session's `.claude/skills/`) — none of these are part of the echo
  plugin, and I have no tool available to confirm which skills (if any beyond the four listed
  above) are loaded for *this* research session. This is **unverified**; do not assume a
  `loop`/`schedule` skill is available to echo without confirming it is actually registered for
  this plugin/session.
  Source: `find / -iname "*.md" -path "*skills*loop*"` and `-path "*skills*schedule*"` (paths
  all outside `<repo-root>`)

### 7. Repo/tooling constraints that shape the design
- The plugin is explicitly standard-library-only Python, no third-party dependency, so any new
  `bin/echo-*` script must use only `subprocess`/`json`/stdlib, matching the existing style of
  `echo-git` and `echo-stage`.
  Source: `lib/echo_common.py:1-6` (module docstring); `CLAUDE.md:23` ("Python 3, standard
  library only... no PyYAML; state is JSON")
- The smoke test (`tests/smoke.sh`) exercises `echo-stage init/approve/next`, `echo-verify`,
  and `echo-git ship --dry-run` end to end; a new post-ship command should get an equivalent
  smoke-test line if it becomes part of the shipped surface.
  Source: `tests/smoke.sh:1-40`

## Options and tradeoffs

1. **New `monitor`/`watch` stage inserted between `ship` and `done` in `STAGES`.**
   For: fits the existing gated-stage machinery (`GATED_STAGES`, `FLOW_STOP_GATES`,
   `/echo:flow` dispatch) so `/echo:status` and `/echo:flow` naturally show and drive it.
   Against: `STATE_VERSION`/`STAGES` is a shared constant read by every `bin/echo-*` script
   and `/echo:flow`'s per-stage table (`commands/flow.md:26-31`); inserting a stage is a
   schema-shaped change affecting `GATED_STAGES` (`lib/echo_common.py:24`), the `hints` dict
   (`bin/echo-stage:111-119`), and any already-`done` items whose `stage` field predates the
   new value. Higher blast radius for a feature that is really "one more automated check", not
   a new phase of the SDLC that needs its own gate/artifact template.

2. **Standalone `bin/echo-watch` (or `echo-ci`) + a new `/echo:watch` command, invoked by
   `/echo:ship` as an optional last step (or run manually after ship).**
   For: no change to `STAGES`/state schema; matches the existing pattern of a thin `bin/`
   determinism layer plus a `commands/*.md` orchestration file (e.g., `echo-verify` +
   `/echo:verify`). Can start as a one-shot poll (`gh pr checks --json ...` and
   `gh api .../pulls/{n}/comments`) that a human or `/echo:flow` re-invokes, avoiding any
   blocking call inside an agent turn; can optionally support `--watch` for a deliberate
   blocking wait when the user wants to sit and watch. Findings can be written to a new
   `.echo/verify/<ticket>-ci.md` or similar artifact reusing the existing `verify_dir()`/
   `review_dir()` helpers (`lib/echo_common.py:126-131`), and reuse the Jira comment ledger
   pattern (`comment-needed`/`comment-done`, `lib/echo_common.py:213-231`) to post a Jira
   comment once on CI failure or once a Claude review comment appears, without double-posting.
   Against: still needs *something* to call it repeatedly for true "continuous" monitoring
   since there is no timer hook (Finding 3); by itself it is a manual/one-shot check unless
   paired with a loop.

3. **Ship-completion Stop-hook style gate (mirrring `echo-verify-gate`) that blocks the
   session from ending while CI is pending/failed for the just-shipped PR.**
   For: reuses the proven fail-open Stop-hook pattern (`bin/echo-verify-gate:1-64`); requires
   no new command, only a new hook script wired in `hooks/hooks.json`.
   Against: only protects *this* session — once the session ends (or the user accepts the
   block and stops anyway, which Stop hooks cannot always prevent across all clients), nothing
   watches the PR further; it cannot proactively surface a review comment left an hour later.
   It answers "don't let me forget to check" more than "continuously monitor".

## Risks and unknowns
- Whether `gh pr view --json statusCheckRollup` is actually a valid field in the installed
  `gh` 2.91.0 was not directly confirmed in this session (the `--json` field list from `gh pr
  view --json bogusfield` was truncated before reaching that field alphabetically past
  `headRefName`). Needs a direct `gh pr view --json statusCheckRollup` check against a real PR
  before being relied on in a design.
- Whether a "Claude review comment" bot is installed on the target GitHub repo/org, and what
  GitHub login it posts under, is unknown — this is outside the echo codebase and was not
  observed anywhere in this session's tools.
- The exact GitHub MCP tool name(s) for *reading* PR comments/reviews (as opposed to the named
  `pull_request_review_write`/`add_comment_to_pending_review` write tools) were not directly
  enumerated in this session; only the server's own instruction text was available, which
  gives a naming convention (`list_*`, `search_*`) but not a concrete read-tool name.
- Whether a `loop` or `schedule` skill is actually registered and usable from within echo (as
  opposed to belonging to unrelated plugins/sessions found on disk) is unverified; no tool was
  available to enumerate this session's loaded skill set beyond echo's own `skills/` directory.
- True "continuous" monitoring across time (not just within one agent turn or one session) has
  no execution substrate in this repo today: no cron, no daemon, no webhook receiver. Any
  design that promises "continuous" monitoring beyond a single command invocation or a single
  blocking `--watch` call is, as far as this research found, not currently buildable with
  stdlib-only `bin/` scripts and existing hooks alone; it would need either a bounded polling
  loop invoked once (blocking for its duration) or a human/agent to re-invoke a one-shot check
  periodically.
- How to avoid duplicate Jira comments/noise if `echo-watch` is invoked multiple times while CI
  is still pending is not designed yet; the existing ledger (`jira/<ticket>.json`) only records
  "posted once ever" per event name (`lib/echo_common.py:219-231`), so a naive reuse would need
  a new event key per meaningfully distinct state (e.g., `ci:failed`, `review:new`) rather than
  a single `ci` key, to allow re-alerting on a *new* failure after a prior success, which was
  not designed here and needs a spec decision.

## Recommendation
Add this as **Option 2**: a standalone `bin/echo-watch` (stdlib Python, following the
`echo-git`/`echo-stage` shape) plus a `/echo:watch` command, run as an explicit optional step
after `/echo:ship` succeeds (not a new `STAGES` entry). Concretely:
- `echo-watch checks --ticket T [--json]` — one-shot: shell out to `gh pr checks --json
  bucket,name,state,link` (or `gh pr view --json statusCheckRollup` once verified) for the
  active/given PR; exit non-zero and print failing check names on failure, matching the
  fail-open-but-informative style of `echo-verify-gate`.
- `echo-watch comments --ticket T [--since <iso timestamp>]` — one-shot: `gh api
  repos/{owner}/{repo}/pulls/{n}/comments` (plus `gh pr view --json comments,latestReviews` for
  conversation-level and formal review comments), filtered by author/timestamp so repeat calls
  only report new items.
- A thin `--watch` mode that loops these two one-shot checks with a sleep and a bound (e.g.,
  max N minutes or until CI resolves), printing incremental updates — this is a *bounded,
  explicit* blocking call the user opts into, not a background daemon, which keeps it feasible
  as a plain stdlib script and honest about what "continuous" can mean in this environment.
- Reuse `jira_ledger`-style per-event tracking (new keys like `ci:failed`, `review:seen:<id>`)
  so re-running `echo-watch` doesn't spam duplicate Jira comments, extending the existing
  pattern in `lib/echo_common.py:213-231` rather than inventing a new mechanism.
- Do not insert a new `STAGES` entry (Option 1): the schema/blast-radius cost is high for a
  feature that is fundamentally "one more check to run", and `ship` -> `done` already models
  ship as the last gated stage (Finding 2). Do not rely solely on a Stop hook (Option 3): it
  only guards a single session and cannot proactively notify after the session ends.
- Before writing an intent/spec for this, resolve the two "Unknown" items above that materially
  affect the design: (1) confirm `statusCheckRollup` (or settle on `gh pr checks --json`
  instead) with a live `gh pr view --json statusCheckRollup` call against a real PR, and
  (2) confirm which GitHub MCP tool (if any, vs. plain `gh` CLI) should be the primary read
  path for review comments, since that changes whether `echo-watch` shells out to `gh` only or
  also documents an MCP-based alternative.

## Sources
- `commands/ship.md` (lines 6-36)
- `bin/echo-git` (lines 1-155, especially 58-135)
- `bin/echo-stage` (lines 1-261, especially 91-119, 185-209)
- `lib/echo_common.py` (lines 1-335, especially 20-58, 90-153, 213-258)
- `hooks/hooks.json` (lines 1-41)
- `bin/echo-verify-gate` (lines 1-68)
- `bin/echo-capture` (lines 1-89)
- `commands/flow.md` (lines 1-80)
- `commands/next.md` (lines 1-28)
- `templates/research.md` (research doc skeleton)
- `skills/research-template/SKILL.md`
- `CLAUDE.md` (repo root, "Conventions" section)
- `tests/smoke.sh` (lines 1-40)
- Command run: `gh --version` -> `gh version 2.91.0 (2026-04-22)`
- Command run: `gh pr checks --help`
- Command run: `gh run watch --help`
- Command run: `gh pr view --help`
- Command run: `gh pr view --json bogusfield` (field list, truncated)
- Command run: `gh api --help`
- Command run: `grep -rniE "watch|monitor|subtask|post-ship|post ship" commands/ bin/ lib/ skills/ agents/ templates/` (no matches)
- Command run: `ls skills/ commands/ agents/ templates/`
- Command run: `find / -iname "*.md" -path "*skills*loop*"` / `-path "*skills*schedule*"`
- URL fetched: https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#list-review-comments-on-a-pull-request
- Named system: this session's "MCP Server Instructions" context, "claude.ai github-custom" section
