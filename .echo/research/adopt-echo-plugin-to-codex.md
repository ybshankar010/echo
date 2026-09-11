# Research: Adopting the echo plugin to OpenAI Codex CLI

- **Question:** understand how we can adopt echo plugin to codex ?
- **Date:** 2026-09-12
- **Ticket or Topic:** adopt-echo-plugin-to-codex (topic, no ticket given)
- **Status:** draft

## Scope
echo is currently a Claude Code plugin (commands, subagents, skills, hooks) wrapping a
runtime-agnostic Python core (`lib/echo_common.py`, `bin/echo-*`). The question is whether
and how that loop (Plan -> Design -> Build -> Test -> Ship, with a plan-guard, a hard
verify-gate, maker-checker review, Jira comments, post-ship watch) can run under OpenAI's
Codex CLI instead of, or alongside, Claude Code.

This answers: what echo depends on today, what Codex actually offers as of this research
(config, AGENTS.md, prompts/skills, MCP, approvals/sandbox, multi-agent), where the two
line up, where they do not, and a phased path. It does not attempt an actual port; no code
was changed.

## Findings

### A. What echo depends on in Claude Code

- The plugin is declared by `.claude-plugin/plugin.json:1-7` (name `echo`, v0.5.0) and
  `.claude-plugin/marketplace.json:1-14` (a local single-plugin marketplace entry pointing
  `source: "./"`). Both are Claude Code plugin-system artifacts, not portable concepts.
  - Source: `.claude-plugin/plugin.json:1`, `.claude-plugin/marketplace.json:1`
- `hooks/hooks.json` wires five lifecycle events to `bin/` scripts:
  - `SessionStart` and `PostCompact` -> `bin/echo-recall` (rehydrate memory into context).
  - `PreToolUse` with `matcher: "Write|Edit|NotebookEdit"` -> `bin/echo-plan-guard` (blocks
    code edits until a plan is approved and the item has reached `build`; exits 2 to block).
  - `Stop` -> `bin/echo-verify-gate` (hard-blocks stopping without a fresh passing verify
    artifact; exits 2 to block) then `bin/echo-capture` (writes recap/episodes).
  - `SessionEnd` -> `bin/echo-capture` again.
  - Source: `hooks/hooks.json:1-42`
- `bin/echo-plan-guard` reads `.echo/state.json` via `ec.load_state()`, checks
  `item["gates"]["plan"] == "approved"` and stage `>= build`, and prints
  `"BLOCKED by ..."` then `sys.exit(2)` to actually stop the tool call; it fails open (exit 0)
  if the repo is not an echo repo or the active item cannot be mapped.
  - Source: `bin/echo-plan-guard:50-89`
- `bin/echo-verify-gate` reads `.echo/verify/<ticket>.md` for a line
  `- exit_code: 0`; if absent or nonzero it prints `"BLOCKED by echo: ..."` and
  `sys.exit(2)`, otherwise exits 0. It only enforces at stage `test`/`ship` and only when
  `config.verify_gate == "block"`.
  - Source: `bin/echo-verify-gate:26-65`
- `commands/*.md` (flow, research, status, intent, approve, next, spec, plan, build, verify,
  review, ship, watch, install-hooks) are Claude Code slash-command definitions (markdown
  with frontmatter, `$ARGUMENTS`, `${CLAUDE_PLUGIN_ROOT}` interpolation).
  - Source: `commands/flow.md:1-101` (example: uses `${CLAUDE_PLUGIN_ROOT}/bin/echo-stage`
    at lines 20, 47, 56, 63-64, 75, 87)
- `agents/*.md` (builder, critic, researcher, reviewer, verifier) are Claude Code subagent
  definitions with `tools:` and `model:` frontmatter, invoked as maker-checker pairs at the
  Plan and Build stages (`critic` over plan/spec, `reviewer` over the builder's diff).
  - Source: `agents/builder.md:1-6` (frontmatter `tools: Read, Write, Edit, Bash, Grep`,
    `model: opus`), `README.md:48-51`
- `skills/*/SKILL.md` (intent-template, plan-template, research-template, spec-template)
  are Claude Code Skills: frontmatter `name`/`description`, loaded by name from commands
  (e.g. `/echo:research` loads `echo:research-template`).
  - Source: `skills/research-template/SKILL.md:1-35`
- Jira progress comments go through the Atlassian MCP tools `getAccessibleAtlassianResources`
  and `addCommentToJiraIssue`, called directly by the command flow (not by `bin/`); the
  deterministic decision of *whether* to post lives in `bin/echo-stage`
  (`comment-needed`/`comment-done`).
  - Source: `commands/flow.md:78-88`, `commands/ship.md:26-30`, `commands/watch.md:23-27`,
    `README.md:55-62`
- The deterministic core (`lib/echo_common.py`, all `bin/echo-*`) imports only Python
  stdlib: `json, os, re, subprocess, time, typing` in `lib/echo_common.py:9-13`, and each
  `bin/echo-*` only imports stdlib plus `echo_common` (checked for
  `echo-capture, echo-git, echo-install-hooks, echo-plan-guard, echo-recall, echo-stage,
  echo-verify, echo-verify-gate`). `echo-watch` was also grepped with the others.
  - Source: command run `grep -n "^import\|^from" lib/echo_common.py`; command run
    `for f in bin/echo-*; do head -20 "$f" | grep -n "import\|sys.path"; done` (2026-09-12,
    this session)
- A grep for `anthropic|openai|claude api` across `lib/` and `bin/` found exactly one hit,
  and it is a string constant for the git commit trailer, not an API dependency:
  `bin/echo-git:21: TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"`.
  - Source: command run `grep -rniE "anthropic|api\.anthropic|claude api|openai" lib/ bin/`
    (2026-09-12, this session); confirmed at `bin/echo-git:21`
- Conclusion: the `bin/`+`lib/` core is runtime-agnostic today. It shells out
  (`subprocess`), reads/writes JSON under `.echo/`, and has no dependency on the Claude API,
  the Claude Code process, or any Anthropic SDK. Everything Claude-Code-specific is in
  `commands/`, `agents/`, `skills/`, `hooks/hooks.json`, and the two `.claude-plugin/*.json`
  manifests.
  - Source: inference from the grep/import findings above plus `CLAUDE.md:16-19` in this
    repo, which states the same architecture split ("`lib/echo_common.py` — all shared
    determinism ... Everything imports it" / "`bin/echo-*` — one CLI per concern")

### B. What Codex CLI offers as extension points

- **AGENTS.md**: Codex reads `AGENTS.md` files before doing any work, using a three-level
  hierarchy: `~/.codex/AGENTS.override.md` then `~/.codex/AGENTS.md` (global), then, walking
  from the git root down to the cwd, `AGENTS.override.md` then `AGENTS.md` per directory
  (project). Files are concatenated root-to-leaf so closer files override earlier guidance;
  at most one file per directory is included, empty files are skipped, and there is a 32 KiB
  default byte limit. This is the same shape as `CLAUDE.md` (project instructions loaded at
  session start) but the docs fetched here do not themselves compare it to CLAUDE.md.
  - Source: URL fetched `https://learn.chatgpt.com/docs/agent-configuration/agents-md`
    (redirected from `https://developers.openai.com/codex/guides/agents-md`), 2026-09-12
- **config.toml** (`~/.codex/config.toml`, or project-scoped `.codex/config.toml` for
  trusted projects) is the single settings surface, comparable in role to `.echo/config.json`
  plus Claude Code's settings, but with a different shape. Verified keys:
  - `notify` (`array<string>`): "Command invoked for notifications; receives a JSON payload
    from Codex." Search results (not the fetched config-reference page) indicate the only
    documented event today is `agent-turn-complete`, fired once when a turn ends, with
    fields like `type`, `thread-id`, `turn-id`, `cwd`, `input-messages`. This looks like a
    one-way notification hook, not a blocking hook (no evidence found that its exit code or
    output can stop or fail the turn, unlike Claude Code's Stop hook which blocks via
    `sys.exit(2)`). Label: inference from search snippets, not independently fetched from a
    primary spec page — flagged in Risks.
    - Source: URL fetched `https://learn.chatgpt.com/docs/config-file/config-reference`
      (redirected from `https://developers.openai.com/codex/config-reference`), 2026-09-12;
      WebSearch "Codex CLI notify command JSON payload event types agent-turn-complete",
      2026-09-12
  - `approval_policy`: `on-request | never | granular` (granular sub-keys
    `sandbox_approval`, `rules`, `mcp_elicitations`, `request_permissions`,
    `skill_approval`, each boolean), plus `approvals_reviewer`: `user | auto_review`.
    - Source: URL fetched `https://learn.chatgpt.com/docs/config-file/config-reference` and
      `https://learn.chatgpt.com/docs/agent-approvals-security` (redirected from
      `https://developers.openai.com/codex/agent-approvals-security`), 2026-09-12
  - `sandbox_mode`: `read-only | workspace-write | danger-full-access`, plus
    `sandbox_workspace_write.network_access` (bool).
    - Source: same two URLs as above
  - `mcp_servers.<id>` table: `command`/`args`/`env` for stdio servers, or `url` (+
    `bearer_token_env_var`) for Streamable HTTP servers; `mcp_servers.<id>.enabled` and
    `default_tools_approval_mode` (`auto | prompt | writes | approve`). MCP config is shared
    across the ChatGPT desktop app, Codex CLI, and IDE extension.
    - Source: URL fetched `https://learn.chatgpt.com/docs/extend/mcp?surface=cli`
      (redirected from `https://developers.openai.com/codex/mcp`), 2026-09-12
  - `agents.enabled` (bool, default true), `agents.default_subagent_model`,
    `agents.max_concurrent_threads_per_session`: a config-driven multi-agent / subagent
    capability exists.
    - Source: URL fetched `https://learn.chatgpt.com/docs/config-file/config-reference`,
      2026-09-12
- **Custom prompts** (Markdown files in `$CODEX_HOME/prompts/`, default `~/.codex/prompts/`,
  invoked as `/prompts:<name>` or `/<name>`) are the closest Codex equivalent to Claude
  Code's `commands/*.md` slash commands, but the docs explicitly mark them **deprecated**:
  "Custom prompts are deprecated. Use skills for reusable instructions that Codex can invoke
  explicitly or implicitly."
  - Source: URL fetched `https://learn.chatgpt.com/docs/custom-prompts` (redirected from
    `https://developers.openai.com/codex/custom-prompts`), 2026-09-12; WebSearch "Codex CLI
    custom prompts slash commands prompts folder", 2026-09-12
- **Skills**: Codex's replacement mechanism. A skill is a directory with a `SKILL.md`
  (YAML frontmatter `name`/`description` + markdown body), stored at `~/.codex/skills/`
  (personal) or `.codex/skills/` (project), optionally with `scripts/`, `references/`,
  `assets/` subfolders. Codex reads the frontmatter to decide when to trigger a skill and
  loads the body only when it fires (explicit invocation or implicit, description-matched
  auto-trigger). Multiple secondary sources state the same `SKILL.md` format is intended to
  be cross-compatible across Codex CLI, Claude Code, Gemini CLI, Cursor, and GitHub Copilot
  "without modification" — this is a strong signal echo's existing `skills/*/SKILL.md` files
  may need little to no change, but it was not verified against a primary OpenAI doc in this
  session (search-result claim only).
  - Source: WebSearch "Codex CLI skills feature ~/.codex/skills SKILL.md", 2026-09-12
    (aggregated from multiple secondary sources: agensi.io, blog.fsck.com); not independently
    fetched from developers.openai.com — flagged in Risks
- **codex exec**: a non-interactive mode that streams progress to stderr and the final
  answer to stdout, defaulting to a read-only sandbox and `approval_policy = "never"" — the
  natural entry point for CI/scripted use analogous to running `bin/echo-*` directly.
  - Source: WebSearch "Codex CLI notify hook approval sandbox exec policy", 2026-09-12
    (secondary source: codex.danielvaughan.com); not independently fetched — flagged in
    Risks
- **Subagents / multi-agent**: `agents.enabled` plus per-role config in `config.toml`
  (model, instructions, sandbox mode, MCP servers per role) and tools described in search
  results as `spawn_agent`, `send_message`, `followup_task`, and a CSV batch fan-out tool
  (`spawn_agents_on_csv`). This is explicit and TOML-configured, contrasted in one secondary
  source against Claude Code's more autonomous "Agent Teams" (peer mailbox, shared task
  list). Not independently verified against a primary OpenAI spec page in this session.
  - Source: WebSearch "Codex CLI subagents multi-agent Task tool equivalent", 2026-09-12
    (secondary sources: codex.danielvaughan.com, morphllm.com); `agents.*` keys themselves
    were confirmed via the fetched config-reference page above
- **No PreToolUse/Stop/SessionStart hook system found**: nothing in the fetched
  `agent-approvals-security` or `config-reference` pages describes a lifecycle hook that
  intercepts a specific tool call before it runs (Claude Code's `PreToolUse` with a tool-name
  matcher) or blocks a session from ending (Claude Code's `Stop`) the way `hooks/hooks.json`
  does. The closest primitives are: `approval_policy`/`sandbox_mode` (gate by
  action-category and filesystem/network boundary, not by "has this ticket's plan been
  approved") and `notify` (a fire-and-forget notification on turn-complete, not a blocker).
  - Source: URL fetched `https://learn.chatgpt.com/docs/agent-approvals-security`, 2026-09-12
    ("the documentation does not describe explicit pre-execution hooks or session-end
    lifecycle callbacks that developers can implement to gate actions" — direct fetch result)

## Options and tradeoffs

1. **Run the `bin/`+`lib/` core unchanged under Codex, orchestrated by AGENTS.md +
   skills, with no automatic gate enforcement.**
   For: the core has zero Claude-specific dependency (Finding A, grep results); `AGENTS.md`
   and Codex Skills are functionally close analogs of `CLAUDE.md` and Claude Code Skills
   (Finding B). Against: plan-guard and verify-gate currently rely on Claude Code's
   `PreToolUse`/`Stop` hooks returning exit code 2 to hard-block (`bin/echo-plan-guard:84-85`,
   `bin/echo-verify-gate:61-64`); no Codex equivalent was found (Finding B, last bullet), so
   under this option the gates become advisory text in AGENTS.md/skills rather than an
   enforced block, unless the agent is disciplined to run `bin/echo-plan-guard`/
   `bin/echo-verify-gate` itself before editing/stopping.

2. **Re-express the command layer as Codex Skills (not deprecated custom prompts) and
   keep the maker-checker loop as explicit `agents.*`-configured subagent calls.**
   For: Skills are the current, non-deprecated Codex mechanism and per secondary sources
   share the same `SKILL.md` shape echo already uses in `skills/*/SKILL.md`; Codex's
   `agents.*` config gives a first-class (if more explicit/TOML-driven) way to spawn a
   builder/critic/reviewer-equivalent instead of Claude's Task-tool subagents. Against: the
   `commands/*.md` files (flow, intent, approve, next, ...) are Claude Code slash commands,
   not skills, and would need to be rewritten as skill directories; the Task-tool subagent
   frontmatter in `agents/*.md` (`tools:`, `model:`) has no confirmed 1:1 Codex equivalent,
   only a generically similar `agents.*` config surface (unverified in depth this session).

3. **Wire the Atlassian MCP the same way and accept partial gate enforcement via
   `approval_policy`/`sandbox_mode` instead of exact plan-guard/verify-gate parity.**
   For: Codex MCP config (`mcp_servers.<id>`, stdio or Streamable HTTP) is confirmed generic
   and should be able to call the same Atlassian MCP server Claude Code uses for
   `addCommentToJiraIssue` (Finding B, MCP bullet), since MCP is a standard protocol, not a
   Claude Code feature. Against: `sandbox_mode`/`approval_policy` gate by action category
   (write scope, network) and are not ticket/stage-aware; they cannot replicate "no edits
   until `plan` is approved for *this* ticket" without the agent voluntarily calling
   `bin/echo-plan-guard` as a script step, which depends on the model following AGENTS.md
   instructions rather than being enforced by the runtime.

## Risks and unknowns

- Whether Codex's `notify` hook payload or exit code can actually **block** a turn (like
  Claude Code's Stop hook exit-2) was not confirmed from a primary source; the evidence
  found (WebSearch snippets, not a fetched spec page) suggests it is a one-way notification
  only. Needs verifying against `https://developers.openai.com/codex/config-advanced` or
  equivalent, or hands-on testing.
- The claim that Codex Skills' `SKILL.md` format is drop-in cross-compatible with Claude
  Code's Skills came only from secondary sources (agensi.io, blog.fsck.com), not a fetched
  OpenAI page. echo's existing `skills/*/SKILL.md` frontmatter (`name`, `description`) should
  be spot-checked against Codex's actual skill loader before assuming zero changes needed.
- The exact shape and reliability of `agents.*` multi-agent config (whether it can express
  the specific builder -> reviewer / plan -> critic maker-checker loop `commands/flow.md`
  and `commands/build.md` implement, including passing the plan/spec artifact paths the way
  `agents/builder.md:12-17` expects) is unverified; the search results describe general
  capability (`spawn_agent`, `send_message`, CSV batch) but not a worked example matching
  echo's loop.
- `codex exec` behavior (defaults, whether `--sandbox`/`--approval-policy` flags can force a
  read-only or workspace-write mode suitable for `/echo:verify`-style checks) was only
  found via a secondary source (codex.danielvaughan.com), not fetched directly.
- Whether Codex CLI can be pointed at a project-scoped `.codex/config.toml` (as opposed to
  only `~/.codex/config.toml`) for MCP servers "for trusted projects only" implies some kind
  of trust prompt/allowlist; the exact trust mechanism and whether it fits a
  single-developer organization workflow is unknown.
- No hands-on Codex CLI session was run in this research (no Codex tool was available in
  this environment); all Codex-side findings are documentation-only. A real port needs a
  Codex CLI install to validate AGENTS.md discovery, skill triggering, and MCP calls
  end-to-end.
- This document does not address licensing/approval to point Codex (an OpenAI-hosted
  product) at the same Atlassian Jira instance organization uses with the Claude Code MCP
  integration; that is an org/security question, not a technical one, and was out of scope
  here.

## Recommendation

Not a full port yet; a phased, low-risk adoption path, because the deterministic core is
already portable but the two enforcement mechanisms (plan-guard, verify-gate) currently
depend on a Claude-Code-only hook primitive that has no confirmed Codex equivalent:

- **Phase 1 (near-zero risk):** Run `bin/echo-stage`, `bin/echo-verify`,
  `bin/echo-plan-guard`, `bin/echo-verify-gate`, `bin/echo-recall`, `bin/echo-capture`,
  `bin/echo-git`, `bin/echo-watch` completely unchanged under Codex (they are plain Python
  stdlib, confirmed in Finding A). For the instruction file, do NOT maintain a separate
  `AGENTS.md`: keep `CLAUDE.md` as the single source of truth and expose it to Codex with a
  symlink `ln -s CLAUDE.md AGENTS.md` (AGENTS.md points at the real CLAUDE.md). Codex reads
  only `AGENTS.md` and has no `@import`/file-reference mechanism, so a prose "see ./CLAUDE.md"
  pointer or an `@./CLAUDE.md` line is read as LITERAL TEXT by Codex, not expanded; the symlink
  is what actually dedupes for Codex. Verified in this repo (2026-09-12): `ln -s CLAUDE.md
  AGENTS.md` reads through to CLAUDE.md and git tracks it as a symlink (mode 120000).

  Tool-by-tool nuance (grounded, 2026-09-12):
  - Codex reads only `AGENTS.md`, no import syntax -> needs the symlink (or a generated
    AGENTS.md) to get CLAUDE.md's content.
  - OpenCode reads `CLAUDE.md` natively (and `~/.claude/CLAUDE.md`), and its config has an
    `instructions` array to list files -> a symlink is not required there; the `./CLAUDE.md`
    reference pattern seen in the wild is OpenCode's own mechanism, not Codex's.
  - The `@path` import syntax is Claude-Code-specific; do NOT put it in a shared `AGENTS.md`.
  - Disputed across sources: whether Claude Code falls back to `AGENTS.md` when no `CLAUDE.md`
    exists. The symlink sidesteps this, since both names then resolve to identical content
    regardless of which a tool prefers.

  Symlink read-through for Codex (2026-09-12): a program opening `AGENTS.md` by path follows
  the symlink at the OS level and gets `CLAUDE.md`'s bytes, so Codex reading `AGENTS.md`
  receives the CLAUDE.md content with no special handling. Two conditions: (1) co-location -
  it is a RELATIVE link, so `CLAUDE.md` must sit in the same directory as the `AGENTS.md`
  symlink; copying `AGENTS.md` alone to a location without the target (e.g. a lone
  `~/.codex/AGENTS.md`) leaves a dangling link. (2) discovery - Codex must find `AGENTS.md` on
  its search path (project root merged up the tree, plus `~/.codex/AGENTS.md`). Not yet
  verified: whether Codex itself does anything unusual with a symlinked instruction file
  (lstat/skip); standard behavior reads through, but confirm in a live Codex session.

  Caveat: symlinks may not survive some Windows checkouts or `git archive` exports, and a
  copied-away `AGENTS.md` can dangle (above); a repo that runs inside its own checkout is safe
  with the symlink, but for dropping echo's guidance into arbitrary projects or a lone global
  location, prefer a tiny generated `AGENTS.md` regenerated from `CLAUDE.md` by a build step
  (a real file, no co-location dependency), never hand-maintained. In that instruction file, document the loop stages and instruct Codex to
  run `bin/echo-plan-guard`/`bin/echo-verify-gate` as manual steps before editing code /
  before ending a turn, since there is no confirmed automatic blocking hook. This gets the
  state machine and artifacts working with zero code change, but the guardrails become
  instruction-following rather than enforced.
- **Phase 2 (final phase for this scope):** Convert the current `commands/*.md` (Claude Code
  slash commands) into Codex Skills under `.codex/skills/` (not the deprecated custom-prompts
  path), reusing the existing `skills/*/SKILL.md` templates largely as-is per the
  (secondary-sourced, needs verifying) cross-compatible `SKILL.md` format. Re-express the
  `agents/*.md` maker-checker roles (builder/critic/reviewer/verifier/researcher) using
  Codex's `agents.*` config (`default_subagent_model`, per-role model/instructions) as the
  closest available multi-agent primitive, accepting it is more explicitly orchestrated than
  Claude's Task tool.

  Scope notes (per the owner, 2026-09-12):
  - **No Atlassian MCP for the Codex version.** Jira progress comments stay a Claude-version-
    only feature; the Codex version does not wire `mcp_servers.<id>` for Atlassian. This is a
    clean simplification because the actual `addCommentToJiraIssue` call lives in echo's
    command/markdown layer, NOT in the `bin/` core (`bin/echo-stage` only keeps the
    `comment-needed`/`comment-done` ledger), and the design already FAILS OPEN when no MCP is
    present. So the Codex loop runs identically; the single difference is that no Jira comment
    is posted as stages complete. The runtime-agnostic ledger logic still runs (harmless
    bookkeeping) and can be wired to Atlassian later if ever wanted, with zero core change.
  - **No Codex-native gate approximation.** A further phase attempting `approval_policy`/
    `sandbox_mode` as a gate is explicitly OUT of scope. echo's hard gates stay enforced only
    on Claude Code; under Codex they are instruction-level (Phase 1), which is accepted.

## Cross-agent plugin authoring (broader context)
Beyond echo specifically, the emerging pattern for "one plugin, many coding agents" is:
- **`AGENTS.md` is the cross-tool instruction standard** adopted by 20+ agents (Codex CLI,
  Cursor, GitHub Copilot, Gemini CLI, Jules, Aider, Zed, Warp, JetBrains Junie, and more);
  Claude Code is the outlier that prefers `CLAUDE.md` but falls back to `AGENTS.md`. The
  symlink above bridges the two.
- **Multi-harness plugin marketplaces already exist** that author once in Claude Code's
  plugin format (agents + skills + commands) and are consumed natively by Codex CLI, Cursor,
  OpenCode, and GitHub Copilot from a single source (e.g. `wshobson/agents`,
  `agentplugins.net`). This is direct precedent that echo's Claude-Code plugin layout can be
  made portable rather than rewritten, and worth studying before hand-porting `commands/` and
  `agents/`.
- Inference: the durable, tool-agnostic asset is echo's `bin/`+`lib/` core plus the
  `SKILL.md`/`AGENTS.md` content; the per-harness wiring (hooks, slash-command registration,
  subagent invocation) is the thin layer that varies and is what these marketplaces normalize.

**Biggest risk to verify hands-on:** whether Codex has *any* primitive that can hard-block a
tool call or a turn end based on custom logic (equivalent to `sys.exit(2)` from
`PreToolUse`/`Stop`). If `notify` truly is fire-and-forget and `approval_policy`/
`sandbox_mode` are the only gating primitives, echo's two hard gates (plan-guard,
verify-gate) cannot be automatically enforced on Codex today, only instructed via
AGENTS.md/skills and left to model compliance, which is a materially weaker guarantee than
the current Claude Code implementation. This should be confirmed with a live Codex CLI
session before committing to Phase 2/3.

## Sources
- `.claude-plugin/plugin.json:1`
- `.claude-plugin/marketplace.json:1`
- `hooks/hooks.json:1-42`
- `bin/echo-plan-guard:50-89`
- `bin/echo-verify-gate:26-65`
- `commands/flow.md:1-101`
- `agents/builder.md:1-34`
- `skills/research-template/SKILL.md:1-35`
- `commands/ship.md:26-30`
- `commands/watch.md:23-27`
- `README.md:36-62`
- `lib/echo_common.py:9-13`
- `bin/echo-git:21`
- `CLAUDE.md:16-19`
- Command run: `grep -n "^import\|^from" lib/echo_common.py` (2026-09-12)
- Command run: `for f in bin/echo-*; do head -20 "$f" | grep -n "import\|sys.path"; done`
  (2026-09-12)
- Command run: `grep -rniE "anthropic|api\.anthropic|claude api|openai" lib/ bin/`
  (2026-09-12)
- URL fetched: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- URL fetched: https://learn.chatgpt.com/docs/config-file/config-reference
- URL fetched: https://learn.chatgpt.com/docs/agent-approvals-security
- URL fetched: https://learn.chatgpt.com/docs/extend/mcp?surface=cli
- URL fetched: https://learn.chatgpt.com/docs/custom-prompts
- WebSearch: "OpenAI Codex CLI AGENTS.md config.toml custom prompts 2026" (2026-09-12)
- WebSearch: "Codex CLI MCP server support config.toml mcp_servers" (2026-09-12)
- WebSearch: "Codex CLI notify hook approval sandbox exec policy" (2026-09-12)
- WebSearch: "Codex CLI custom prompts slash commands prompts folder ~/.codex/prompts"
  (2026-09-12)
- WebSearch: "Codex CLI subagents multi-agent Task tool equivalent" (2026-09-12)
- WebSearch: "Codex CLI skills feature ~/.codex/skills SKILL.md" (2026-09-12)
- WebSearch: "Codex CLI notify command JSON payload event types agent-turn-complete"
  (2026-09-12)
- WebSearch: "building plugins compatible across multiple coding agents Claude Code Codex
  Cursor AGENTS.md standard" (2026-09-12)
- URL fetched: https://codex.danielvaughan.com/2026/05/27/agent-instruction-files-agents-md-claude-md-cross-tool-portability-codex-cli/
  (2026-09-12) — Codex reads only AGENTS.md; Claude Code prefers CLAUDE.md, falls back to
  AGENTS.md; recommended dedup is a symlink; no @import in Codex/Claude (GEMINI.md has @file).
- Named systems: https://github.com/wshobson/agents (multi-harness plugin marketplace for
  Claude Code, Codex, Cursor, OpenCode, Copilot) and https://agentplugins.net/ (author once,
  consumed by multiple agents) — cited for the cross-agent authoring pattern (2026-09-12).
- WebSearch: "OpenCode AGENTS.md instructions reference CLAUDE.md file import; does Codex CLI
  support file import in AGENTS.md" (2026-09-12).
- URL: https://opencode.ai/docs/rules/ (OpenCode reads AGENTS.md/CLAUDE.md; `instructions`
  config array) and gist https://gist.github.com/zeke/c6bed98a445e559b0d3563087b5e6764
  (OpenCode reads ~/.claude/CLAUDE.md). Disputed fallback claim: https://agyn.io/blog/claude-md-agents-md-compatibility
  (says Claude Code has no AGENTS.md fallback) vs. the danielvaughan article above (says it
  does) — flagged as unresolved; symlink sidesteps it. Command run (2026-09-12): `ln -s
  CLAUDE.md AGENTS.md` in a temp git repo -> read-through works, git mode 120000.
