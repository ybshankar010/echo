# Intent: echo — a personal AI-native SDLC plugin

- **Ticket:** FEAT-3816
- **Stage:** Plan
- **Author:** redacted@example.invalid
- **Status:** approved (Plan gate passed)

## Problem
My development loop is fast at writing code but slow and inconsistent at the
human-speed stages around it: pinning down what I'm actually building, keeping a
written plan before I code, verifying "done" really means tested, and shipping
through the organization's GitHub PR and Jira process. Context also evaporates between
sessions — when I come back to a task (or a session compacts) I re-derive where I
was. Anthropic's "AI-native SDLC playbook" describes a looped, artifact-driven
process that fixes exactly this, but it is written for enterprise adoption and
nothing packages it for a single developer.

## Proposed outcome
A local Claude Code plugin, **echo**, that makes the playbook's loop turnkey for
one developer. Echo drives a work item through **Plan → Design → Build → Test →
Ship** as version-controlled markdown artifacts, with an explicit human gate at
each boundary, deterministic guardrails (hooks), and durable file-based memory so
no session starts cold. Success feels like: I type `/echo:intent`, answer a few
questions, and echo walks me stage by stage — refusing to let me write code before
an approved plan, refusing to stop a session before verification passes, and
handling the branch/commit/rebase/PR flow with the Jira ticket enforced.

## Affected users / systems
- **User:** me (solo developer). Not a team rollout in v1.
- **Claude Code:** installed as a local plugin via a single-plugin marketplace
  (`/plugin install echo@echo-local`). Uses commands, skills, subagents, and hooks.
- **Per-repo working tree:** echo writes committed state under `.echo/`
  (`artifacts/`, `stage.yaml`, `verify/`, `recap.md`, `episodes.jsonl`).
- **git + GitHub (`gh`):** the Ship stage creates branches/commits/PRs.
- **organization's Jira ticket policy:** every commit/PR must carry a ticket id `[A-Z]+-[0-9]+`.

## Constraints
- **Scope: solo-dev loop only.** Out of scope for v1 (future/team): managed MDM
  settings, Claude Security scans, Claude Tag, org marketplace distribution, DORA
  dashboards, and the Maintain stage's control-band automation.
- **Verification gate is a HARD block** on session Stop until a fresh passing
  verify artifact exists for the active task.
- **State lives in `.echo/` and is committed** (not gitignored).
- **Multi-stack** verification: Python, JS/TS, Java/Kotlin (auto-detected).
- **Grounding:** artifacts and gate state are files, inspectable in git; no hidden
  state, no fabricated verification.
- Determinism lives in `bin/` Python CLIs; generation is Claude guided by template
  skills. Reference the sibling `momo` plugin only for the CC plugin file format,
  not its philosophy.

## Resolved decisions (were open questions)
1. **Global tier deferred.** v1 uses per-repo `.echo/` only; `~/.claude/echo/`
   cross-project index/facts comes later.
2. **`echo-plan-guard` = hard-deny with escape hatch.** Blocks code edits when
   `stage < build` or `plan.md` not approved; overridable via a documented flag in
   `.echo/config`.
3. **Ship opens the PR via `gh`.** branch → commit → rebase develop → push → open
   PR (ticket body). Pauses and shows conflicts on rebase failure.

## How we know it worked (leading signals)
- I can drive `/echo:intent → /echo:spec → /echo:plan → build → /echo:verify →
  /echo:ship` end to end on a scratch repo.
- The hard gate actually blocks a Stop with no passing verify.
- The commit-msg hook actually blocks a ticketless commit.
- A new session, after compaction, tells me the active stage + last recap.
