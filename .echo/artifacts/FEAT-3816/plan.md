# Plan: echo — build implementation plan

- **Ticket:** FEAT-3816
- **Stage:** Build (kickoff)
- **Derived from:** `.echo/artifacts/spec.md` (approved)
- **Status:** approved (Build gate passed)
- **State format decision:** JSON at `.echo/state.json` (stdlib `json`, no YAML
  dependency). Supersedes the `stage.yaml` naming in spec §3; schema is unchanged.

## Files that change (create)
```
echo/
  .claude-plugin/plugin.json           # name echo, version 0.1.0
  .claude-plugin/marketplace.json      # name echo-local, plugin source ./
  lib/echo_common.py                   # paths, ticket regex, stack detect, yaml I/O, git helpers
  bin/echo-stage                       # stage.yaml state machine (init/status/approve/next)
  bin/echo-recall                      # SessionStart/PostCompact context injection
  bin/echo-capture                     # Stop: write recap.md + episodes.jsonl
  bin/echo-verify                      # run stack tests, write .echo/verify/<task>.md
  bin/echo-verify-gate                 # Stop: hard-block if no fresh passing verify
  bin/echo-plan-guard                  # PreToolUse Write|Edit guard
  bin/echo-git                         # ship flow (branch/commit/rebase/push/PR) + --dry-run
  bin/echo-install-hooks               # install commit-msg ticket gate
  hooks/hooks.json                     # wire the 5 hooks
  commands/{status,intent,approve,next,spec,plan,verify,review,ship,install-hooks}.md
  agents/{verifier,reviewer}.md
  skills/{intent-template,spec-template,plan-template}/SKILL.md
  templates/{intent.md,spec.md,plan.md,CLAUDE.md,REVIEW.md}
  CLAUDE.md                            # echo's own repo instructions (one page)
  README.md, INSTALL.md, .gitignore
  tests/test_echo.py                   # unit tests for lib + CLIs (pytest)
  tests/smoke.sh                       # end-to-end CLI smoke on a temp repo
```
No `.py` extension on `bin/` scripts; each is `#!/usr/bin/env python3`, `chmod +x`,
and inserts `../lib` on `sys.path` to import `echo_common`.

## Order of work
1. **`lib/echo_common.py` first** (everything imports it): repo/`.echo` path
   helpers, `TICKET_RE = re.compile(r"[A-Z]+-[0-9]+")`, minimal YAML load/dump
   (stdlib only — hand-rolled reader for our flat schema, no PyYAML dependency),
   `load_stage()/save_stage()`, `detect_stacks(repo)`, `git(*args)` runner,
   `STAGES` list + `next_stage()`.
2. **`bin/echo-stage`** — subcommands `init`, `status`, `approve`, `next`. `next`
   returns non-zero + message if the current gate ≠ approved. Pure state; prints
   what the calling command should generate next.
3. **`bin/echo-verify` + `bin/echo-verify-gate`** — verify runs detected commands,
   writes artifact with `exit_code`; gate reads freshest artifact for active task,
   exit 2 if missing/failing/stale (older than latest source change is out of scope
   for v1 — "fresh" = exists and exit_code 0 since last stage entry).
4. **`bin/echo-plan-guard`** — parse stdin JSON, allow when path under `.echo/` or
   ends `.md` in artifacts/docs, else block per `config.plan_guard` + gate.
5. **`bin/echo-recall` + `bin/echo-capture`** — recall prints stage+artifact+recap;
   capture derives episode from `git` (branch, `--name-only`, last commit) and
   rewrites `recap.md`.
6. **`bin/echo-git` + `bin/echo-install-hooks`** — ship flow with `--dry-run`
   proven first; install-hooks writes an idempotent `# echo-managed` commit-msg hook.
7. **Wiring:** `hooks/hooks.json`, `commands/*.md`, `agents/*.md`, `skills/*`,
   `templates/*`.
8. **Manifests + docs:** `.claude-plugin/*`, `CLAUDE.md`, `README.md`, `INSTALL.md`,
   `.gitignore`.
9. **Tests:** `tests/test_echo.py` (lib + echo-stage + plan-guard + git dry-run),
   `tests/smoke.sh` (init→approve→next→verify on a temp git repo).

Parallelizable after step 2: the CLI groups in steps 3, 4, 5, 6 touch disjoint
files and may be built concurrently if desired.

## Risks
- **State format:** resolved to JSON (`.echo/state.json`) — no YAML parser needed.
  `config.yaml` knobs also move to `.echo/config.json` for one consistent format.
- **`gh` may be absent / unauthenticated:** `echo-git` must detect and print a clear
  message + the manual command rather than crashing.
- **Hook exit-2 semantics:** must block only for the intended event; every gate
  fails open when it cannot map the active item (no `.echo/`, unknown active).
- **Cross-platform:** target macOS/Linux; use `python3`, avoid bashisms in CLIs.

## Proof (how this build is verified — feeds Test stage)
- `pytest tests/test_echo.py` green: ticket regex, stack detection on fixture repos,
  `stage.yaml` round-trip, `next` gate-block, `plan-guard` allow/deny, `echo-git`
  `--dry-run` output + no-ticket failure.
- `bash tests/smoke.sh` green: creates a temp git repo, runs
  `echo-stage init → status → approve → next`, `echo-verify` on a trivial passing
  command writes an artifact, `echo-verify-gate` blocks then passes.
- Manual: `/plugin marketplace add <abs path>` → `/plugin install echo@echo-local`,
  then `/echo:status` responds and `commit-msg` hook blocks a ticketless commit.

## Definition of done
All Proof checks pass; echo installs locally; the loop
`/echo:intent → spec → plan → build → /echo:verify → /echo:ship` is drivable on a
scratch repo; the hard verify gate and commit-msg ticket gate both demonstrably fire.
