# Intent: Codex compatibility Phase 2 (commands to Skills, agents to agents.*)

- **Ticket:** FEAT-6833
- **Stage:** Plan
- **Author:** echo-contributor
- **Status:** draft (awaiting `/echo:approve`)

## Problem
Phase 1 made echo's guidance readable by Codex (the `AGENTS.md` symlink + a how-to section) and
confirmed the `bin/` core runs unchanged. But echo's actual workflow surface, its slash
`commands/*.md` (14) and Task-tool `agents/*.md` (5), is still Claude-Code-only. A Codex user has
to drive the loop by hand from the CLI how-to; there are no Codex-native Skills or subagents.
Phase 2 ports that surface to Codex's own primitives, grounded in the verified formats in
`.echo/research/codex-phase2-skills-and-agents-formats.md`.

## Proposed outcome
echo ships Codex-native artifacts, authored to the primary-source-verified formats, with every
unverifiable gap documented rather than hidden:
- **Commands -> Codex Skills.** Each `commands/*.md` becomes a Skill at
  `.agents/skills/echo-<name>/SKILL.md` (the current, non-deprecated mechanism; NOT the
  deprecated `~/.codex/prompts/` path). Minimal frontmatter `name` + `description` (which matches
  echo's own skill templates), body = the adapted command instructions. Since Skills have no
  `$ARGUMENTS`/`argument-hint` equivalent, the ticket-id/goal extraction moves into the Skill body
  prose (the same "extract the ticket from what the user typed" pattern the commands already use).
- **Agents -> per-agent Codex TOML.** Each `agents/*.md` becomes a `.codex/agents/<name>.toml`
  with `name`, `description`, `developer_instructions` (the role prompt), and `model`. The
  report-only roles (critic/reviewer/verifier) carry an explicit "never edit files" instruction
  plus, where expressible, `sandbox_mode = read-only`, because Codex has no per-agent tool
  allowlist to enforce echo's `tools:` restriction structurally.
- **Skill templates discoverable by Codex.** The 4 `skills/*-template/SKILL.md` are made
  reachable under `.agents/skills/` (copy or symlink; decided in spec) since their minimal schema
  already works under Codex.
- **Honest invocation/orchestration doc.** A section (in the flow Skill body and referenced from
  the CLAUDE.md Codex section) explains that maker-checker orchestration is prose-driven
  (natural-language delegation), because no Codex cross-agent spawn primitive is verified.

## Affected users / systems
- **Codex users of echo:** gain `/skills`-invocable (or auto-triggered) echo Skills and named
  subagents, instead of hand-driving the CLIs.
- **echo internals:** new `.agents/skills/echo-*/SKILL.md`, new `.codex/agents/*.toml`, a
  copy/symlink of the template skills into `.agents/skills/`, and doc updates. The `bin/`/`lib/`
  core, the Claude Code `commands/`, `agents/`, `skills/`, `hooks/` are unchanged (Phase 2 adds
  Codex-native siblings, it does not rewrite the Claude Code surface).
- **External:** OpenAI Codex CLI (its Skills discovery and `[agents]`/per-agent-TOML config).

## Constraints
- Author to the primary-source-verified formats only (research doc): Skills at `.agents/skills/`,
  `SKILL.md` frontmatter `name` + `description`; per-agent TOML fields `name`, `description`,
  `developer_instructions`, optional `model`/`sandbox_mode`/`mcp_servers`. Do NOT invent fields.
- **Do not build against unverified primitives as if they work.** The cross-agent spawn tool
  (Task-tool equivalent) is UNVERIFIED; orchestration is documented as prose delegation, not coded
  against a guessed `spawn_agent` schema.
- No change to the Claude Code plugin surface or the `bin/`/`lib/` core; no regression (existing
  62 tests + smoke stay green).
- Stdlib-only if any script is added (none planned); no em dashes in new prose.
- Carry Phase 1's owner decisions: no Atlassian MCP on the Codex path; gates stay advisory (no
  Codex-native enforcement); `CLAUDE.md` remains the single source of truth.
- Non-goals: runtime verification in a live Codex session (flagged as required follow-up, not done
  here since no Codex is installed); the deprecated custom-prompts path; any hooks/gate
  enforcement on Codex; changing the Claude Code files.

## Open questions
- **Scope of the port:** all 14 command Skills, or a core loop subset first (flow, intent, spec,
  plan, build, verify, ship, status, approve, next)? Leaning: port all 14 for completeness since
  each is mechanical, but spec may stage it. `install-hooks` has no Codex equivalent (skip or
  document as N/A).
- **Template-skill placement:** copy the 4 `skills/*-template` into `.agents/skills/`, or symlink
  each? Leaning: symlink (single source, consistent with Phase 1), if Codex follows symlinked
  skill dirs; else copy with a note. Verify.
- **Agent TOML location:** research shows per-agent files under `.codex/agents/` while Skills use
  `.agents/skills/` (two different dirs per the docs). Confirm both against the installed Codex
  version at build time; the Skills path changed once recently (openai/codex#15972).
- **`sandbox_mode` granularity for the verifier:** it must run tests (Bash) but not edit; whether
  Codex expresses "execute but not write" is unconfirmed. Leaning: document the limitation, use
  the closest sandbox setting, rely on prose.
- **Runtime verification:** none is possible here. Leaning: ship the artifacts with a prominent
  "verify against your installed Codex CLI (skill discovery, subagent spawn, `.agents/skills`
  path) before relying on this" note, and treat a live-Codex pass as a separate follow-up.

## How we know it worked
- Each ported Skill exists at `.agents/skills/echo-<name>/SKILL.md` with valid `name` +
  `description` frontmatter and a body that carries the command's instructions (a check can grep
  each expected path and assert non-empty frontmatter).
- Each of the 5 agents exists at `.codex/agents/<name>.toml` with `name`, `description`,
  `developer_instructions` present; report-only agents contain an explicit no-edit instruction.
- The template skills are reachable under `.agents/skills/`.
- The Claude Code surface is unchanged and existing 62 tests + smoke stay green (no regression);
  new smoke checks assert the Codex artifacts exist and are well-formed.
- Docs plainly state the verified-vs-unverified boundary (orchestration prose-only, tool-allowlist
  not enforced, runtime not tested), so a reader is not misled about parity.
