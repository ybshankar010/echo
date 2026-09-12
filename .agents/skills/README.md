# echo command Skills (Codex port)

This directory holds the Codex-facing port of echo's Claude Code commands. Each
`echo-<name>/SKILL.md` mirrors the matching `/echo:<name>` command and drives the same
loop through the stdlib `bin/echo-*` CLIs, which are unchanged. The agent role TOMLs the
skills delegate to live under `.codex/agents/`.

echo is a Claude Code plugin first. These Skills and agent TOMLs are additive: they do
not change the plugin surface under `commands/`, `agents/`, `skills/`, `hooks/`, `bin/`,
or `lib/`.

## Known limitations (Codex)

These are the honest boundaries of the Codex port. Read them before relying on it.

- Orchestration is prose-driven. Under Claude Code the commands spawn subagents through
  the Task tool; under Codex the Skill bodies instead ask Codex in prose to delegate to
  the matching role agent under `.codex/agents/`. There is no structured hand-off, so the
  quality of delegation depends on the model following the prose.
- Tool restrictions are not enforced by Codex the way plugin frontmatter enforces them
  in Claude Code. A report-only role is told "never edit files; report only" and, where
  Codex supports it, `sandbox_mode = "read-only"`, but nothing in this repo guarantees
  Codex honors those hints at runtime.
- Skills have no structured arguments. A Claude command declares `argument-hint` and
  reads `$ARGUMENTS`; a Skill has no such contract. Each Skill reads the ticket id
  (`[A-Z]+-[0-9]+`) and any goal text from what the user typed, and never fabricates a
  ticket.
- Gates are advisory here. The plan-guard and verify-gate hooks are Claude Code hooks;
  under Codex the stage gates are advisory guidance the model is asked to respect, not a
  hard block.
- The researcher's web access is unverified. Whether a spawned Codex agent actually gets
  web search or fetch tools is unverified and depends on the Codex environment.
- `install-hooks` is N/A. The `/echo:install-hooks` command wires Claude Code hooks and
  has no Codex equivalent, so it is intentionally not ported.
- None of this is verified in a live Codex session. The formats here are authored to
  static shapes (SKILL.md frontmatter, agent TOML) and checked by the repo's smoke tests
  for structure only. The runtime behavior is not verified in a live Codex session; treat
  everything here as best-effort until confirmed live.

## Jira comments are Claude-only

Where a Claude command posts Jira progress comments through the Atlassian MCP tools,
that behavior is Claude-only and is skipped under Codex. echo never changes the Jira
status field, and never posts without a valid ticket, on either surface.
