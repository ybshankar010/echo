# Intent: Codex compatibility for the echo plugin

- **Ticket:** FEAT-6833
- **Stage:** Plan
- **Author:** echo-contributor
- **Status:** draft (awaiting `/echo:approve`)

## Problem
echo is a Claude Code plugin: its loop is driven by Claude-Code-specific glue (slash
`commands/*.md`, Task-tool `agents/*.md`, `skills/*/SKILL.md`, and `hooks/hooks.json`). A user
who works in OpenAI Codex today gets none of it. But research
(`.echo/research/adopt-echo-plugin-to-codex.md`) established that echo's determinism (all
`bin/echo-*` + `lib/echo_common.py`) is pure Python stdlib with no Anthropic/OpenAI dependency,
so the core is already runtime-agnostic; only the thin per-harness wiring is Claude-specific.
The gap is that nothing tells Codex how to read echo's guidance or drive its loop.

## Proposed outcome
echo is usable from OpenAI Codex, delivered as the research's Phase 1 (near-zero risk), with the
Phase 2 command/agent port scoped as an explicit follow-on:
- **Single source of truth for instructions:** `CLAUDE.md` stays canonical; Codex reads it via a
  symlink `AGENTS.md -> CLAUDE.md` (Codex reads only `AGENTS.md` and has no `@import`, so a prose
  pointer would be inert; the symlink delivers the content). Research verified read-through and
  git symlink tracking (mode 120000).
- **Codex setup docs:** a short section (in `CLAUDE.md`, so both tools see it) telling a Codex
  user how to drive the loop by calling the `bin/echo-*` CLIs directly, and to run
  `bin/echo-plan-guard` / `bin/echo-verify-gate` as manual pre-edit / pre-turn steps, since Codex
  has no confirmed blocking-hook equivalent.
- **The `bin/` core runs unchanged under Codex** (already stdlib; confirmed by research).

## Affected users / systems
- **Codex users of echo:** gain the loop (state machine, artifacts, gates as manual steps).
- **Claude Code users:** unaffected. The symlink does not change what Claude Code reads
  (`CLAUDE.md` directly), and no `commands/agents/hooks` behavior changes.
- **echo internals:** adds `AGENTS.md` (symlink) and a Codex section in `CLAUDE.md`; possibly a
  small `.codex/` scaffold and a generator script for the no-symlink fallback. No change to
  `bin/`, `lib/`, or the existing Claude-Code plugin surface.

## Constraints
- **No Atlassian MCP for the Codex path** (owner decision): Jira progress comments stay a
  Claude-version-only feature. This is free because the `addCommentToJiraIssue` call lives in the
  command/markdown layer, not the `bin/` core, and echo already fails open with no MCP. The Codex
  loop runs identically minus the Jira comments.
- **No Codex-native gate approximation** (owner decision): do not attempt `approval_policy` /
  `sandbox_mode` as a gate. echo's hard gates stay enforced only on Claude Code; under Codex they
  are instruction-level, which is accepted.
- Keep `CLAUDE.md` as the single source of truth; never hand-maintain two instruction files.
- Stdlib-only Python, no third-party dependency; no em dashes in user-facing strings/docs.
- Do not regress the Claude Code plugin: existing tests and smoke stay green.
- Non-goals for this build: the full `commands/*.md` -> Codex Skills and `agents/*.md` ->
  `agents.*` port (that is Phase 2, a separate follow-on); Cursor/OpenCode/Copilot support;
  Windows-specific symlink handling beyond documenting the generated-`AGENTS.md` fallback.

## Open questions
- **Symlink vs generated file:** default to the symlink `ln -s CLAUDE.md AGENTS.md` (works when
  echo runs inside its own checkout; research verified). Do we also ship a tiny generator
  (`bin/echo-...` or a make step) that writes `AGENTS.md` from `CLAUDE.md` for repos/Windows
  checkouts where symlinks do not survive? Leaning: yes, a small optional generator, since it
  removes the co-location/Windows fragility the research flagged. Settle in spec.
- **Codex symlink read (unverified):** research confirmed OS-level read-through but did not test
  Codex's own handling of a symlinked `AGENTS.md`. Leaning: proceed with the symlink and note it
  as a hands-on verification item; the generator is the fallback if Codex mishandles it.
- **Where the Codex how-to lives:** a section inside `CLAUDE.md` (so the symlinked `AGENTS.md`
  carries it to Codex automatically) vs a separate `docs/codex.md`. Leaning: inside `CLAUDE.md`.
- **Any `.codex/` scaffold now?** e.g. a `.codex/skills/` placeholder or `config.toml` example.
  Leaning: documentation only in this build; real skill/agent porting is Phase 2.

## How we know it worked
- `AGENTS.md` resolves to `CLAUDE.md`'s content (a reader opening `AGENTS.md` gets the CLAUDE.md
  text); git tracks it as a symlink (mode 120000). If a generator ships, running it produces an
  `AGENTS.md` whose content matches `CLAUDE.md`.
- `CLAUDE.md` contains a Codex section describing how to drive the loop via `bin/echo-*` and the
  manual gate steps.
- The `bin/` core still runs (`py_compile` clean) and the existing unit + smoke suites stay green
  (no Claude-Code regression).
- A concrete, documented command sequence a Codex user runs to drive the loop through the
  `bin/echo-*` CLIs (e.g. `echo-stage init` -> write artifacts -> `echo-stage approve`/`next` ->
  `echo-verify`), with `bin/echo-plan-guard` / `bin/echo-verify-gate` invoked manually as the
  advisory gate steps. Testable as: following the documented steps reaches an approved-plan state
  and a green `echo-verify` without relying on any Claude Code hook.
