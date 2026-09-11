# Spec: echo — a personal AI-native SDLC plugin

- **Ticket:** FEAT-3816
- **Stage:** Design
- **Derived from:** `.echo/artifacts/intent.md` (approved)
- **Status:** approved (Design gate passed)

## 1. Overview
echo is a local Claude Code plugin that drives one work item through
**Plan → Design → Build → Test → Ship** as version-controlled markdown artifacts,
with an explicit human gate (`approve`) at each boundary, deterministic guardrails
(hooks + a `bin/` CLI layer), and file-based memory that survives session restarts
and compaction. Determinism lives in Python CLIs under `bin/`; generation of
artifact content is done by Claude, guided by template skills.

## 2. Stage model
Stages, in order: `intent → spec → plan → build → test → ship → done`.

Each stage has:
- an **artifact** (markdown) it produces, and
- a **gate** (`pending | approved`) the human flips with `/echo:approve`.

`/echo:next` advances exactly one stage and refuses if the current gate is not
`approved`. The mapping stage → artifact:

| Stage | Artifact | Generator |
|---|---|---|
| intent | `.echo/artifacts/intent.md` | `intent-template` skill |
| spec | `.echo/artifacts/spec.md` | `spec-template` skill (reads intent.md) |
| plan | `.echo/artifacts/plan.md` | `plan-template` skill (reads spec.md) |
| build | code changes | main thread, guarded by `echo-plan-guard` |
| test | `.echo/verify/<task>.md` | `verifier` subagent via `echo-verify` |
| ship | branch/commit/PR | `echo-git` |

## 3. State schema — `.echo/stage.yaml`
```yaml
version: 1
active: FEAT-3816
items:
  FEAT-3816:
    title: Build echo plugin
    stage: intent
    gates:
      intent: approved
      spec: pending
      plan: pending
      build: pending
      test: pending
      ship: pending
    artifacts:
      intent: .echo/artifacts/intent.md
      spec: null
      plan: null
    created: 2026-09-04T00:00:00Z
    updated: 2026-09-04T00:00:00Z
```
Owned exclusively by `bin/echo-stage`. Commands never hand-edit it.

### `.echo/config.yaml` (per-repo knobs)
```yaml
version: 1
jira_required: true          # commit-msg + ship enforce [A-Z]+-[0-9]+
plan_guard: deny             # deny | warn | off  (escape hatch)
plan_guard_override: false   # true = temporarily allow code edits pre-plan
base_branch: develop         # ship rebases onto origin/<this>; fallback main/master
verify_gate: block           # block | warn  (Stop behavior)
```

## 4. Commands (`commands/*.md`)
All are thin: they call `bin/` for determinism and use skills for generation.

| Command | Behavior |
|---|---|
| `/echo:status` | `echo-stage status` → active item, current stage, gate states, next action |
| `/echo:intent [desc]` | Init item if none; write `intent.md` via `intent-template`; set stage=intent |
| `/echo:spec` | Require intent approved; write `spec.md` via `spec-template` |
| `/echo:plan` | Require spec approved; write `plan.md` via `plan-template` |
| `/echo:approve` | `echo-stage approve` → flip current stage gate to `approved` |
| `/echo:next` | `echo-stage next` → advance if gate approved, then run the new stage's generator |
| `/echo:verify [cmd]` | Spawn `verifier`; record `.echo/verify/<task>.md`; used by Test stage + Stop gate |
| `/echo:review` | Spawn `reviewer` over the working diff using `REVIEW.md` |
| `/echo:ship` | `echo-git ship` → branch → commit → rebase → push → PR (ticket enforced) |
| `/echo:install-hooks` | `echo-install-hooks` → install commit-msg ticket gate in the repo |

## 5. Hooks (`hooks/hooks.json`)
| Event | Command | Effect |
|---|---|---|
| `SessionStart` | `echo-recall` | Inject active stage + latest artifact + last recap into context |
| `PostCompact` | `echo-recall` | Same re-injection after a compaction |
| `PreToolUse` (matcher `Write|Edit`) | `echo-plan-guard` | If `plan_guard=deny` and (`stage<build` or plan gate ≠ approved) and no override → exit 2 (block) with the reason + how to override |
| `Stop` | `echo-verify-gate` | If `verify_gate=block` and no fresh passing `.echo/verify/<active>.md` → exit 2 (block) naming the verify command |
| `Stop` | `echo-capture` | Write `recap.md` + append `episodes.jsonl` (git-derived) |

Hook I/O contract: scripts read the hook JSON on stdin, print human-readable
guidance to stdout/stderr, and use **exit code 2 to block**. `echo-plan-guard`
inspects `tool_input.file_path` and treats non-code paths (`.echo/**`, `*.md`
artifacts, docs) as always-allowed so gating never blocks writing the artifacts
themselves.

## 6. Subagents (`agents/*.md`)
```
verifier  — tools: Bash, Read
  Runs the detected test/build/lint sequence (or a given command), exercises the
  changed behavior, reports pass/fail with the exact commands + output tail.
  Never edits files. Output is written by echo-verify to .echo/verify/<task>.md.

reviewer  — tools: Read, Grep
  Reads REVIEW.md and applies its passes (bugs / security / compliance) to the
  working diff. Reports findings ranked by severity; caps nits. Never edits.
```

## 7. Stack detection (`lib/echo_common.py`)
Detect by marker files in repo root (first match wins per category):
- **Python:** `pyproject.toml` / `setup.py` / `pytest.ini` / `tox.ini` → test `pytest`; lint `ruff check .` (fallback `flake8`).
- **JS/TS:** `package.json` → read `scripts.test` / `scripts.lint`; run `npm test` / `npm run lint` (respect `pnpm`/`yarn` lockfile if present).
- **Java/Kotlin:** `build.gradle(.kts)` → `./gradlew test`; `pom.xml` → `mvn -q test`.
If multiple stacks present, run each detected category's test command in sequence.
If none detected, `echo-verify` requires an explicit command argument.

## 8. Git / PR flow (`bin/echo-git ship`)
1. Resolve ticket from branch name (`[A-Z]+-[0-9]+`); else from `--ticket` arg; else FAIL (no fabrication).
2. If on `base_branch`/main/master, create `TICKET/<slug>` from a `--desc`.
3. `git add -A` (or staged only with `--staged`); commit `TICKET: <message>` including the Co-Authored-By trailer.
4. `git fetch origin`; `git rebase origin/<base_branch>` (fallback main/master). On conflict: STOP, print conflicting files, do not auto-resolve.
5. `git push -u origin <branch>`.
6. `gh pr create` — title `TICKET: <title>`, body starts `Ticket: TICKET` then a summary. If a PR already exists, update it.
`--dry-run` prints every step without executing. Irreversible ops (force push) require explicit confirmation.

## 9. Memory model
| Type | Location | Written by |
|---|---|---|
| Long-term project | `.echo/artifacts/{intent,spec,plan}.md`, `CLAUDE.md` | stage generators |
| Working | `.echo/stage.yaml`, `.echo/recap.md` | `echo-stage`, `echo-capture` |
| Episodic | `.echo/episodes.jsonl` | `echo-capture` (ts, branch, changed files, commits, stage) |
| Verify proof | `.echo/verify/<task>.md` | `echo-verify` (ts, exit_code, command, output tail) |
Global tier (`~/.claude/echo/`) is **deferred** per intent decision 1.

## 10. Flagged concerns (policy / risk)
- **Security:** never commit secrets; `echo-git` does not add a secret scanner in v1
  but must not print tokens; recommend gitleaks as a follow-up. `echo-recall`
  injects only artifact/recap text, never env or credentials.
- **Compliance (organization):** commit + PR ticket enforcement is mandatory and lives
  in two independent layers (the `commit-msg` git hook and `echo-git`), so the
  policy holds even outside Claude.
- **Safety:** all gates **fail open when they cannot map the active item** (no
  `stage.yaml`, or active item unknown) so echo never bricks an unrelated repo.
  Destructive/irreversible git actions require confirmation.
- **Determinism vs. generation:** anything that must be reproducible (state, gates,
  stack detection, git steps, ticket regex) is in `bin/`/`lib/`; only prose
  generation is model-driven.

## 11. Non-goals (v1)
Managed MDM settings, Claude Security scans, Claude Tag, org marketplace
distribution, DORA dashboards, Maintain-stage control bands, and the global memory
tier. All noted as future/team work.

## 12. Acceptance criteria (feeds plan.md "Proof")
- `bin/echo-stage` round-trips `stage.yaml`: init, status, approve, next; `next`
  blocks on an unapproved gate.
- `bin/echo-verify` detects the stack, runs it, writes a verify artifact with the
  real exit code; `verify_gate=block` blocks Stop without a fresh pass.
- `echo-plan-guard` blocks a code Write pre-plan and allows artifact/doc writes.
- `echo-git ship --dry-run` prints the full flow and fails with no ticket.
- `commit-msg` hook blocks a ticketless commit message.
- Local install works: `/plugin marketplace add <path>` → `/plugin install echo@echo-local`; `/echo:status` responds.
