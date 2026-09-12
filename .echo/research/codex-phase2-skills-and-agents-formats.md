# Research: Codex Phase 2 formats - custom prompts/Skills and subagents/agents.*

- **Question:** For Phase 2 of adopting echo to OpenAI Codex (porting `commands/*.md` to
  Codex custom prompts/Skills, and `agents/*.md` Task-tool subagents to Codex's
  subagent/`agents.*` mechanism), what are the exact, current, primary-sourced Codex formats?
  The prior research (`.echo/research/adopt-echo-plugin-to-codex.md`) flagged these as
  secondary-sourced and unverified; this doc re-verifies against primary OpenAI docs.
- **Date:** 2026-09-12
- **Ticket or Topic:** codex-phase2-skills-and-agents-formats (topic, no ticket given)
- **Status:** draft

## Scope

Answers, each grounded: (1) do Codex custom prompts/slash commands exist, and are they
deprecated in favor of Skills, with exact directory/schema/invocation for both; (2) the
exact `config.toml`/TOML schema for Codex subagents, compared field-by-field to echo's
`agents/*.md` frontmatter; (3) the concrete invocation model an echo user would actually
type in Codex to trigger a "command" that orchestrates subagents; (4) what genuinely does
not port; (5) a mapping table for every echo command/agent/skill/hook to its Codex
equivalent (or "no equivalent"). Does not attempt an actual port or write any Codex config;
no code was changed. Does not re-litigate the hooks-lifecycle gap already established in
the prior research doc beyond citing it once for continuity.

**Important correction surfaced in this session:** the prior research doc stated Codex
Skills live at `~/.codex/skills/` (personal) or `.codex/skills/` (project), sourced only
from WebSearch snippets (agensi.io, blog.fsck.com), not a fetched primary page. Fetching the
primary OpenAI doc directly in this session shows a **different, current** path scheme:
`.agents/skills` (repo-scoped, walking up from cwd to repo root), `$HOME/.agents/skills`
(user-scoped), `/etc/codex/skills` (admin-scoped), plus a built-in system scope. See Finding
1.3 below. This is flagged as a correction, not a restatement.

## Findings

### 1. Custom prompts / slash commands in Codex CLI

**1.1 Custom prompts exist but are documented as deprecated, in favor of Skills.**
The official page states verbatim: "Deprecated. Use skills for reusable prompts" and
"Custom prompts are deprecated. Use skills for reusable instructions that Codex can invoke
explicitly or implicitly."
- Source: URL fetched `https://learn.chatgpt.com/docs/custom-prompts` (redirected 308 from
  `https://developers.openai.com/codex/custom-prompts`), 2026-09-12.

**1.2 Custom prompt file format and location (while still supported):**
- Directory: `~/.codex/prompts/` by default (`$CODEX_HOME/prompts/`). Only top-level
  Markdown files are scanned; subdirectories are ignored.
- Format: Markdown with YAML front matter; documented fields are `description:` and
  `argument-hint:`.
- Argument substitution: positional `$1`..`$9` (space-separated args), named uppercase
  vars supplied as `KEY=value` (e.g. `$FILE`, `$TICKET_ID`), `$ARGUMENTS` for the whole
  argument string, `$$` for a literal dollar sign.
- Invocation: type `/` to open the slash menu, then `/prompts:<name>` (e.g.
  `/prompts:draftpr`), supplying arguments, then Enter.
- Source: URL fetched `https://learn.chatgpt.com/docs/custom-prompts`, 2026-09-12.
- Compare to echo: `commands/flow.md:1-6` frontmatter is `description:` +
  `argument-hint: <TICKET-ID> <goal> [--research]`, and the body uses
  `$ARGUMENTS` directly (`Orchestrate the echo SDLC loop end to end for: $ARGUMENTS`).
  This is close to a 1:1 field match (`description`, `argument-hint`, `$ARGUMENTS`) between
  Claude Code's command frontmatter and Codex's (now-deprecated) custom-prompt frontmatter.
  - Source: `commands/flow.md:1-6` (this repo)
- A live GitHub issue against `openai/codex` (opened 2026-03-27, closed as "not planned")
  reports that upgrading codex-cli from 0.116.0 to 0.117.0 made both custom skills and
  custom prompts disappear ("custom skills and custom prompts are gone"), i.e. the `/skills`
  and `/prompts` commands stopped finding previously-installed items. This corroborates that
  the skills/prompts discovery mechanism changed around that release, consistent with the
  directory-scheme correction in Finding 1.3.
  - Source: URL fetched `https://github.com/openai/codex/issues/15972`, 2026-09-12
  - Inference: the 0.117.0 change is plausibly when the skills search path moved from a
    `.codex/skills`-style location to `.agents/skills` (Finding 1.3), but this specific
    causal link is not confirmed by a changelog; labeled as inference.

**1.3 Skills are the current, non-deprecated mechanism. Exact directories (corrected from
prior research):**
- Repo-scoped (REPO): `.agents/skills` in the current working directory, parent
  directories, and the repository root (i.e. Codex walks up looking for `.agents/skills`).
- User-scoped (USER): `$HOME/.agents/skills`.
- Admin-scoped (ADMIN): `/etc/codex/skills`.
- System-scoped (SYSTEM): built-in skills shipped by OpenAI.
- Source: URL fetched `https://learn.chatgpt.com/docs/build-skills` (redirected 308 from
  `https://developers.openai.com/codex/skills`), 2026-09-12.
- A secondary source independently states "Codex-native `.agents/skills/` support" as a
  recognized directory, corroborating the primary-fetched page (not a standalone
  verification, but consistent).
  - Source: WebSearch "openai/codex github skills.rs .agents/skills .codex/skills source
    code", 2026-09-12 (aggregated snippet referencing VoltAgent/awesome-agent-skills and
    openai/skills repos)
- **This directly contradicts the prior research doc's claim of `~/.codex/skills/` /
  `.codex/skills/`**, which was sourced only from WebSearch aggregation
  (`.echo/research/adopt-echo-plugin-to-codex.md:143-154`), not a direct fetch. Treat the
  prior doc's paths as superseded by this session's direct fetch.

**1.4 `SKILL.md` schema:**
- Required frontmatter: `name` (skill identifier), `description` ("Explain exactly when
  this skill should and should not trigger").
- No other frontmatter fields are documented as required or standard on the fetched page.
- Body: free-form Markdown instructions below the frontmatter.
- Optional directory members alongside `SKILL.md`: `scripts/` (executable code),
  `references/` (documentation), `assets/` (templates/resources), and
  `agents/openai.yaml` (optional UI/policy metadata for the ChatGPT desktop app: fields
  seen in search results are `displayname`, `shortdescription`, `iconsmall`, `iconlarge`,
  `brandcolor`, `defaultprompt`, plus `interface`/`policy`/`dependencies` groupings).
- Source: URL fetched `https://learn.chatgpt.com/docs/build-skills`, 2026-09-12; a second
  WebSearch pass corroborates the same minimal frontmatter (`name`, `description`) and the
  `agents/openai.yaml` optional file.
  - Source: WebSearch "developers.openai.com codex skills SKILL.md frontmatter schema",
    2026-09-12

**1.5 Discovery and invocation of Skills:**
- Explicit: in Codex CLI or the IDE extension, run `/skills` to list, or type `$` followed
  by the skill name to invoke directly.
- Implicit: "ChatGPT and Codex can choose a skill when your task matches the skill
  `description`" (auto-trigger based on the description field, no explicit invocation
  needed).
- Context budget: the initial skill list Codex loads is capped at roughly 2% of the context
  window or 8,000 characters, favoring descriptions for brevity when many skills are
  installed (i.e. only the frontmatter is loaded up front; the body loads when a skill
  actually fires).
- Source: URL fetched `https://learn.chatgpt.com/docs/build-skills`, 2026-09-12.

**1.6 Is Codex's `SKILL.md` schema the SAME as Claude Code's?**
- Verified: this repo's `skills/research-template/SKILL.md:1-4` frontmatter is exactly
  `name: research-template` and `description: <one paragraph>`, nothing else, followed by
  a Markdown body -- structurally identical to the two required Codex fields (`name`,
  `description`) plus free-form Markdown body found in Finding 1.4.
  - Source: `skills/research-template/SKILL.md:1-4` (this repo); fetched Codex skills page
    above.
- On the minimal two-field frontmatter, the schemas match. What is NOT verified as
  identical: Claude Code Skills support additional optional frontmatter (e.g.
  `allowed-tools`, `license`, per Anthropic's own skills docs, not fetched in this
  session) that were not checked against Codex's optional-field list; and Codex's
  `agents/openai.yaml` sidecar file (UI metadata for the ChatGPT desktop app) has no
  Claude Code equivalent. Conclusion: same minimal schema, not necessarily same full
  superset of optional fields. Label: **partially verified** (core two fields confirmed
  identical; extended-field parity not checked against a fetched Claude Code skills spec
  page this session).

### 2. Subagents / `agents.*` in Codex

**2.1 Global `[agents]` table in `config.toml`:**

| Field | Type | Meaning (as documented) |
|---|---|---|
| `agents.enabled` | boolean, default `true` | Enable or disable multi-agent tools |
| `agents.max_concurrent_threads_per_session` | number | Cap concurrently open spawned-agent threads, excluding the primary |
| `agents.default_subagent_model` | string | Default model for spawned agents |
| `agents.default_subagent_reasoning_effort` | string | Default reasoning effort for spawned agents |
| `agents.interrupt_message` | boolean, default `true` | Record a model-visible message when an agent turn is interrupted |

- Source: URL fetched `https://learn.chatgpt.com/docs/agent-configuration/subagents`
  (redirected 308 from `https://developers.openai.com/codex/subagents`), 2026-09-12.

**2.2 Per-agent custom TOML files** (under `~/.codex/agents/` or `.codex/agents/`, one file
per named agent):

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Agent identifier; overrides a built-in agent (`default`, `worker`, `explorer`) if the name matches |
| `description` | Yes | Purpose text |
| `developer_instructions` | Yes | The agent's system/role prompt |
| `model` | No | Per-agent model override |
| `model_reasoning_effort` | No | Per-agent reasoning-effort override |
| `sandbox_mode` | No | Per-agent sandbox policy |
| `mcp_servers` | No | Per-agent MCP server access |
| `skills.config` | No | e.g. can set `enabled = false` for a specific skill for that agent |

- Model/reasoning-effort resolution order: explicit spawn value -> the agent's own
  `[agents]`-file field -> the global `agents.default_subagent_model` /
  `default_subagent_reasoning_effort` -> parent agent's setting (i.e. inherits upward if
  nothing more specific is set).
- Source: URL fetched `https://learn.chatgpt.com/docs/agent-configuration/subagents`,
  2026-09-12.

**2.3 No tool-name allow/deny list field found.** The documented per-agent TOML fields
(`name`, `description`, `developer_instructions`, `model`, `model_reasoning_effort`,
`sandbox_mode`, `mcp_servers`, `skills.config`) do not include anything resembling Claude
Code's `tools:` frontmatter (an explicit whitelist of tool names like `Read, Write, Edit,
Bash, Grep`). `sandbox_mode` and `mcp_servers` gate by filesystem/network scope and which
MCP servers are reachable, not by a named list of built-in tools (Read/Write/Edit/Bash/
Grep-equivalents). Confirmed by directly asking the fetched page for this and getting: "The
documentation does not mention that custom agent TOML files can restrict which tools an
agent may access."
- Source: URL fetched `https://learn.chatgpt.com/docs/agent-configuration/subagents`,
  2026-09-12 (targeted re-fetch for this specific question).

**2.4 How one agent invokes another: NOT formally documented on the fetched page.** The
primary doc describes delegation only in natural-language terms: "Ask Codex in an app chat
to delegate independent parts of the work to subagents," with an example prompt "Spawn one
agent per point, wait for all of them, and summarize the result for each point." No tool
name, function signature, or parameter list (e.g. a `spawn_agent(agent_type, model,
prompt)` call) is documented on this page.
- Source: URL fetched `https://learn.chatgpt.com/docs/agent-configuration/subagents`,
  2026-09-12 (explicitly re-queried for "how does one agent invoke another").
- Secondary sources (not independently fetched, named for completeness only) describe tool
  names `spawn_agent`, `send_message`, `followup_task`, and a CSV batch fan-out tool
  `spawn_agents_on_csv`, and one open GitHub issue confirms `spawn_agent` accepts
  `agent_type` plus model/prompt overrides but "no parameter to say 'spawn the agent defined
  in `.codex/agents/security-reviewer.toml`'" -- i.e. even that secondary source says named
  custom-agent files and the spawn tool do not yet compose cleanly.
  - Source: WebSearch "Codex CLI config.toml agents subagent default_subagent_model
    spawn_agent", 2026-09-12 (secondary: codex.danielvaughan.com); **UNVERIFIED against a
    primary OpenAI doc** -- flagged, not independently fetched.

**2.5 Comparison to echo's `agents/*.md` frontmatter.** Read directly in this session:

| echo field (`agents/*.md`) | Example (builder.md / critic.md) | Codex per-agent TOML equivalent |
|---|---|---|
| `name` | `builder`, `critic` | `name` (same concept, string identifier) |
| `description` | one-paragraph purpose | `description` (same concept) |
| `tools` | `Read, Write, Edit, Bash, Grep` (builder); `Read, Grep, Bash` (critic, report-only) | **no equivalent found** (Finding 2.3); closest proxy is `sandbox_mode` (write vs read-only) plus `mcp_servers`, which gate by scope/protocol, not by named built-in tool |
| `model` | `opus` (builder), `sonnet` (critic, reviewer, verifier, researcher) | `model` (same concept, per-agent override) |
| (n/a) | -- | `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config` (no echo equivalent; echo has no reasoning-effort or MCP-per-role concept today) |
| body (role instructions) | free-form Markdown role prompt | `developer_instructions` (same concept: a string carrying the role prompt) |

- Source: `agents/builder.md:1-6`, `agents/critic.md:1-6`, `agents/reviewer.md:1-6`,
  `agents/verifier.md:1-6`, `agents/researcher.md:1-6` (this repo, read in full this
  session); Codex fields per Finding 2.1/2.2 above.

**2.6 Can echo's maker-checker (builder/critic/reviewer/verifier/researcher) be expressed
in Codex `agents.*`?** Partially, with a real gap:
- `name`, `description`, `model`, and the role prompt (`developer_instructions`) map
  cleanly, one field to one field (Finding 2.5).
- What does **not** map: (a) echo's `tools:` restriction (e.g. critic/reviewer/verifier are
  intentionally report-only -- `Read, Grep, Bash`, no `Write`/`Edit` -- to enforce
  "checker never edits" at the frontmatter level); Codex has no documented per-agent
  tool-allowlist field, so this constraint would have to be enforced by
  `developer_instructions` prose ("never edit files") plus, at best, `sandbox_mode =
  read-only` for that agent's spawned thread -- a coarser, filesystem-wide control, not a
  per-tool-name allowlist. (b) The exact hand-off of concrete artifact paths that
  `agents/builder.md:12-17` and `agents/critic.md:13-17` describe (the caller passes
  `.echo/artifacts/<ticket>/plan.md` etc., taken from `echo-stage status`'s `Artifacts:`
  line) has no documented Codex primitive; it would have to be done via whatever the
  (undocumented, Finding 2.4) spawn/delegate mechanism accepts as a prompt string. (c) the
  maker-checker loop's orchestration logic itself (build -> reviewer runs on the diff;
  plan -> critic runs on the plan; a human approves the gate in between) is currently
  encoded in `commands/*.md` prose steps, not in a `config.toml` structure -- Codex's
  `agents.*` only defines *what an agent is*, not *the sequence in which agents are called
  for a given loop stage*; that sequencing would still have to live in prose (a Skill body)
  that itself asks Codex to delegate, since Finding 2.4 shows no documented programmatic
  orchestration API.
  - Source: `agents/builder.md:1-34`, `agents/critic.md:1-35` (this repo); Findings 2.1-2.4
    above (Codex docs).

### 3. Invocation model: how would `/echo:flow` actually work in Codex?

- A user would NOT get a Claude-Code-style plugin-registered `/echo:flow` slash command
  with typed argument parsing the way `commands/flow.md`'s frontmatter (`argument-hint:
  <TICKET-ID> <goal> [--research]`) provides today, because:
  - If ported as a (deprecated) custom prompt: it would live at
    `~/.codex/prompts/echo-flow.md` and be invoked as `/prompts:echo-flow NPI-1234 do the
    thing`, using `$ARGUMENTS`/`$1`/`$TICKET_ID`-style substitution (Finding 1.2) -- but
    OpenAI's own docs say not to build new things on this path since it is deprecated.
  - If ported as a Skill (the recommended path): it would live at
    `.agents/skills/echo-flow/SKILL.md` (repo-scoped, Finding 1.3) with `name: echo-flow`
    and a `description` written so Codex's implicit trigger matches "drive the echo loop
    for a ticket," OR the user explicitly runs `/skills` and picks it, or types `$echo-flow`
    (Finding 1.5). There is no documented positional-argument syntax for Skills equivalent
    to `$ARGUMENTS`/`$1` for custom prompts (Finding 1.4 lists no argument-hint-equivalent
    field); a GitHub issue thread explicitly discusses skills lacking first-class named
    arguments that custom prompts had. So the ticket id and goal would have to be typed as
    part of the free-text prompt to Codex, then extracted by the skill's own instructions
    (mirroring what `commands/flow.md:14-15` already does today: "Extract a Jira ticket id
    ... from the arguments").
    - Source: WebSearch "OpenAI Codex CLI custom prompts deprecated skills SKILL.md
      developers.openai.com", 2026-09-12 (GitHub issue title: "Update $skill-creator
      guidance to cover named-arg migration from custom prompts BEFORE custom prompts
      deprecation") -- **UNVERIFIED against the primary skill-creator doc itself**, only
      the issue title/summary was read via WebSearch; flagged as needing a direct fetch of
      that skill-creator guidance before final design.
  - Orchestrating subagents from within that Skill: per Finding 2.4, there is no documented
    formal tool call; the Skill body would have to instruct Codex in prose to "delegate to
    a builder-role agent, then a critic-role agent" the way `commands/flow.md` already
    instructs the (Claude Code) main thread in prose to invoke the Task tool for
    `agent: critic` etc. -- i.e. the mechanism is the same *shape* (prose instructing
    delegation) but the underlying primitive Codex exposes for that delegation is
    unverified beyond "ask Codex in an app chat to delegate ... to subagents" (Finding 2.4).
- **There is no confirmed Codex equivalent to Claude Code's `Skill` tool (an explicit
  tool-call to load a named skill's body into context) or `Task` tool (an explicit
  tool-call to spawn a named subagent and get its result back inline) as a documented,
  named, callable primitive** -- Codex's documented mechanisms are slash-menu/`$`-prefix
  UI actions (Finding 1.5) and natural-language delegation requests (Finding 2.4), not
  tool-call primitives with a stable name and parameter schema the way Claude Code's `Task`
  tool has `subagent_type`/`description`/`prompt` parameters. This is the single largest
  concrete gap for Phase 2 design.
  - Source: Findings 1.5, 2.4 above (both from directly fetched primary Codex docs,
    2026-09-12); absence-of-evidence framed explicitly as such, not asserted as "Codex has
    no such tool" beyond what these two fetched pages show.

### 4. What genuinely does not port (beyond the already-known hooks gap)

- **No per-agent tool allowlist** (Finding 2.3): echo's `tools:` frontmatter, which
  encodes "critic/reviewer/verifier never get `Write`/`Edit`," has no Codex field to
  enforce it structurally; it would degrade to prose instruction plus, at best, a
  coarser `sandbox_mode = read-only` for that spawned thread.
- **No documented named tool for cross-agent invocation with a stable parameter schema**
  (Finding 2.4): echo's `commands/build.md`/`commands/plan.md` orchestration (spawn
  builder, then spawn reviewer, hand each specific artifact paths) has no confirmed Codex
  primitive to lean on; it is prose-driven at best today.
- **No argument-hint / positional-argument mechanism for Skills** (Finding 3, GitHub issue
  reference): the `$ARGUMENTS`/`$1`/`argument-hint:` pattern all 14 of echo's
  `commands/*.md` rely on (confirmed present in `commands/flow.md:3,6`) only exists on the
  deprecated custom-prompts path, not on the recommended Skills path; porting to Skills
  means giving up structured argument parsing at the frontmatter level.
- **Directory-path churn risk**: Finding 1.3's `.agents/skills` location plus the
  0.116.0 -> 0.117.0 breakage reported in `openai/codex#15972` (Finding 1.2) show the Skills
  discovery mechanism has changed at least once recently; a Phase 2 design should not
  hard-code a path without re-checking against whatever Codex CLI version is actually
  installed at build time.
- **Hooks lifecycle (carried forward, not re-derived here):** the prior research doc's
  finding that no Codex primitive was found equivalent to Claude Code's blocking
  `PreToolUse`/`Stop` hooks (`sys.exit(2)`) still stands; this session did not re-search it
  and defers to `.echo/research/adopt-echo-plugin-to-codex.md` Finding B (last bullet) for
  that gap. echo's five hook wirings, confirmed again this session at
  `hooks/hooks.json:1-41` (`SessionStart`, `PostCompact` -> `echo-recall`; `PreToolUse`
  matcher `Write|Edit|NotebookEdit` -> `echo-plan-guard`; `Stop` -> `echo-verify-gate` then
  `echo-capture`; `SessionEnd` -> `echo-capture`), have no confirmed Codex equivalent.
  - Source: `hooks/hooks.json:1-41` (this repo, re-read this session);
    `.echo/research/adopt-echo-plugin-to-codex.md` Finding B (prior session, not re-verified
    here).

## Options and tradeoffs

1. **Port `commands/*.md` to Codex Skills under `.agents/skills/<name>/SKILL.md`** (not the
   deprecated custom-prompts path). For: this is the current, non-deprecated, and
   directory-verified mechanism (Finding 1.3); the frontmatter is a strict subset of what
   echo's own skill templates already use (Finding 1.6). Against: loses structured argument
   substitution (`$ARGUMENTS`/`$1`/`argument-hint:`, Finding 4); the ticket id / goal
   extraction logic currently in frontmatter + `$ARGUMENTS` (`commands/flow.md:3,6,14-15`)
   would have to move entirely into the Skill body's own free-text parsing instructions.

2. **Port `commands/*.md` to Codex custom prompts under `~/.codex/prompts/`.** For:
   field-for-field the closest match to Claude Code's frontmatter (`description`,
   `argument-hint`, `$ARGUMENTS`, Finding 1.2 vs `commands/flow.md:1-6`) -- minimal
   rewrite. Against: OpenAI's own docs explicitly deprecate this path (Finding 1.1); a
   GitHub issue shows this mechanism actively breaking across a recent version bump
   (Finding 1.2); building new Phase 2 work on a documented-deprecated feature is a poor
   bet for a "final phase" of this scope.

3. **Port `agents/*.md` to per-agent Codex TOML files under `.codex/agents/`.** For:
   `name`, `description`, `model`, and the role prompt map cleanly (Finding 2.5); this is a
   real, documented, TOML-schema primitive, not a guess. Against: no tool-allowlist field
   (Finding 2.3) means the "checker never edits" guarantee that echo's `tools:` frontmatter
   gives today (e.g. `agents/critic.md:5`: `tools: Read, Grep, Bash`, no `Write`/`Edit`)
   degrades to prose plus, at best, `sandbox_mode`; and the actual maker-checker sequencing
   (build then review, plan then critic) still has to live in a Skill's prose, since there
   is no documented programmatic orchestration API (Finding 2.4).

4. **Do not port the maker-checker loop's enforcement; keep it advisory.** For: matches
   the prior research doc's already-accepted Phase 1/2 scope note ("No Codex-native gate
   approximation," `.echo/research/adopt-echo-plugin-to-codex.md:314-316`) and is
   consistent with this session's findings that neither tool-allowlists (Finding 2.3) nor
   blocking hooks (carried-forward finding, Section 4) exist on Codex today. Against: this
   is a materially weaker guarantee than Claude Code's plan-guard/verify-gate, and should
   be stated plainly in any Phase 2 spec rather than implied.

## Risks and unknowns

- **Directory path for Skills may still be in flux.** Finding 1.3 is from a direct fetch
  today (2026-09-12), but `openai/codex#15972` shows the skills-discovery path already
  changed once across a recent release (0.116.0 -> 0.117.0). A Phase 2 spec should
  re-confirm the installed Codex CLI version's actual skill search path (e.g. by running
  `codex --version` and checking release notes, or testing `/skills` in a live session)
  before hard-coding `.agents/skills/`.
- **No primary-sourced tool name/schema for cross-agent invocation.** Finding 2.4: the
  fetched subagents doc describes delegation only in natural language; `spawn_agent`,
  `send_message`, `followup_task`, `spawn_agents_on_csv` are named only in secondary
  sources (codex.danielvaughan.com, morphllm.com) and one GitHub issue, not independently
  fetched from a primary OpenAI page in this session. This is the single biggest unknown
  for designing how a ported `/echo:flow`-equivalent Skill would actually spawn a
  builder/critic/reviewer/verifier sequence.
- **Named-argument migration story for Skills is unresolved.** A GitHub issue title
  references `$skill-creator` guidance for "named-arg migration from custom prompts BEFORE
  custom prompts deprecation," implying OpenAI itself considers this an open gap, but the
  actual `$skill-creator` guidance content was not fetched in this session (only the issue
  title/summary via WebSearch). Needs a direct fetch of that skill-creator skill's SKILL.md
  (likely in `github.com/openai/skills`) before the Phase 2 spec commits to an
  argument-passing design.
- **Whether `agents/openai.yaml`'s `policy` field can express an invocation trigger
  equivalent to echo's per-stage gate logic** (e.g. only auto-triggering the `plan` skill
  when `.echo/state.json` says stage is at `spec`) is unknown; the fetched page mentions
  `policy` only as a UI/invocation-rule concept for the ChatGPT desktop app, not CLI
  behavior, and was not explored deeper in this session.
- **No hands-on Codex CLI session was run.** As in the prior research doc, all findings
  here are documentation-only (fetched pages plus this repo's own files); a real Phase 2
  build needs a live Codex CLI install to confirm skill triggering, subagent spawning, and
  the `.agents/skills` search path end to end.
- **Tool-restriction gap (Finding 2.3) is stated as "not found in the documented fields,"
  not "does not exist."** It is possible a tool-restriction mechanism exists via
  `sandbox_mode` combinations or an undocumented field not surfaced by the fetched page;
  this should be treated as "unconfirmed," not "confirmed absent."

## Recommendation

Proceed with Option 1 (Skills under `.agents/skills/`) for the command layer and Option 3
(per-agent TOML under `.codex/agents/`) for the maker-checker roles, both accepted as
"documented primitive with real gaps" rather than "fully equivalent," and explicitly scope
the Phase 2 spec to:
- keep the ticket-id/goal argument extraction logic in each Skill's prose body (since
  Finding 4 shows Skills have no `argument-hint`/`$ARGUMENTS` equivalent), mirroring what
  `commands/flow.md:14-15` already does in prose for the ticket-id extraction step (the
  `$ARGUMENTS` substitution itself would not carry over, only the "read this from what the
  user typed" instruction pattern);
- state plainly, not silently drop, that the `tools:` allowlist (report-only agents never
  editing) becomes a prose instruction plus at-best `sandbox_mode`, not an enforced
  restriction (Finding 2.3, Option 3 above);
- treat the cross-agent invocation mechanism (Finding 2.4) as the top item to verify
  hands-on before writing the Phase 2 spec's plan/build orchestration section, since no
  primary-sourced tool schema was found; a live Codex CLI session testing an actual
  "spawn a builder-role subagent and get its diff back" round trip should happen before
  committing to a specific Skill-body wording for `commands/build.md`'s equivalent; and
- re-verify `.agents/skills` against the actually-installed Codex CLI version at
  implementation time, given the documented churn (`openai/codex#15972`).

This is not yet enough evidence to write a Phase 2 spec that claims exact parity anywhere
except the `name`/`description`/`model` fields; the argument-passing and cross-agent
invocation mechanics need either a further doc fetch (the `$skill-creator` guidance) or a
live Codex session before the spec locks in specifics.

## A concrete mapping table

echo surfaces confirmed by `ls commands/ agents/ skills/` (this repo, this session):

```
commands/: approve.md, build.md, flow.md, install-hooks.md, intent.md, next.md, plan.md,
           research.md, review.md, ship.md, spec.md, status.md, verify.md, watch.md  (14)
agents/:   builder.md, critic.md, researcher.md, reviewer.md, verifier.md  (5)
skills/:   intent-template, plan-template, research-template, spec-template  (4)
```//

Note: the goal text said "13 commands"; the actual `ls` this session shows 14 files under
`commands/`. Using the verified count.

| echo surface | Codex equivalent | Notes / gap |
|---|---|---|
| `commands/flow.md` | Skill at `.agents/skills/echo-flow/SKILL.md` | Loses `argument-hint`/`$ARGUMENTS`; ticket-id extraction moves to prose (Finding 3) |
| `commands/research.md` | Skill `.agents/skills/echo-research/SKILL.md` | Same as above; this Skill would itself load the `research-template` skill body |
| `commands/intent.md`, `spec.md`, `plan.md`, `build.md`, `verify.md`, `review.md`, `ship.md`, `watch.md`, `status.md`, `next.md`, `approve.md` | one Skill each under `.agents/skills/echo-<name>/SKILL.md` | Same pattern; each still shells out to the unchanged `bin/echo-*` core (per the prior research doc's Finding A, not re-verified here) |
| `commands/install-hooks.md` | **no equivalent** | No confirmed Codex hook-registration surface exists to install into (Section 4, carried-forward hooks gap) |
| `agents/builder.md` | `.codex/agents/builder.toml` (`name`, `description`, `developer_instructions`, `model`) | No `tools:` allowlist equivalent (Finding 2.3); builder already needs write access so this matters less here |
| `agents/critic.md` | `.codex/agents/critic.toml` | `tools: Read, Grep, Bash` (no Write/Edit) has no enforced Codex equivalent (Finding 2.3); becomes prose + optional `sandbox_mode = read-only` |
| `agents/reviewer.md` | `.codex/agents/reviewer.toml` | Same tool-restriction gap as critic |
| `agents/verifier.md` | `.codex/agents/verifier.toml` | Same tool-restriction gap; also runs `Bash` for tests, so `sandbox_mode` would need to permit execution while still denying edits -- not confirmed as expressible (Finding 2.3 does not show a "execute but do not write" granularity beyond the three-way `sandbox_mode` enum from the prior research doc) |
| `agents/researcher.md` | `.codex/agents/researcher.toml` | Needs `WebSearch`/`WebFetch`-equivalent tool access; Codex's tool surface for a spawned agent is not itself enumerated on the fetched subagents page (unverified whether spawned agents get web tools by default) |
| `skills/intent-template`, `plan-template`, `research-template`, `spec-template` (`SKILL.md`) | Same minimal frontmatter (`name`, `description`) works unchanged under either Claude Code or Codex per Finding 1.6 | Directory would need to also exist at (or be copied/symlinked to) `.agents/skills/` for Codex to discover it, alongside wherever Claude Code expects `skills/` (this repo's existing top-level `skills/` dir vs Codex's `.agents/skills/` path is a different location, so some copy/symlink strategy is needed -- not designed in this doc) |
| `hooks/hooks.json` (`SessionStart`, `PostCompact`, `PreToolUse`, `Stop`, `SessionEnd`) | **no equivalent found** | Carried forward from prior research; `notify` (fire-and-forget, `agent-turn-complete`) is the closest Codex primitive and is not a blocker (prior doc's Finding B, not re-verified this session) |

## Sources

- URL fetched: `https://learn.chatgpt.com/docs/custom-prompts` (redirected 308 from
  `https://developers.openai.com/codex/custom-prompts`), 2026-09-12
- URL fetched: `https://learn.chatgpt.com/docs/build-skills` (redirected 308 from
  `https://developers.openai.com/codex/skills`), 2026-09-12
- URL fetched: `https://learn.chatgpt.com/docs/agent-configuration/subagents` (redirected
  308 from `https://developers.openai.com/codex/subagents`), 2026-09-12 -- fetched twice
  this session, once for the general schema and once specifically re-queried for
  cross-agent invocation and tool-restriction fields
- URL fetched: `https://github.com/openai/codex/issues/15972`, 2026-09-12
- WebSearch: "OpenAI Codex CLI custom prompts deprecated skills SKILL.md
  developers.openai.com", 2026-09-12
- WebSearch: "developers.openai.com codex skills SKILL.md frontmatter schema", 2026-09-12
- WebSearch: "Codex CLI config.toml agents subagent default_subagent_model spawn_agent",
  2026-09-12
- WebSearch: "openai/codex github skills.rs skill_loader .agents/skills .codex/skills
  source code", 2026-09-12
- `commands/flow.md:1-20` (this repo)
- `agents/builder.md:1-34` (this repo)
- `agents/critic.md:1-35` (this repo)
- `agents/reviewer.md:1-28` (this repo)
- `agents/verifier.md:1-27` (this repo)
- `agents/researcher.md:1-9` (this repo)
- `skills/research-template/SKILL.md:1-35` (this repo)
- `hooks/hooks.json:1-41` (this repo)
- Command run: `find <repo-root> -iname "SKILL.md" -path
  "*research-template*"`, 2026-09-12
- Command run: `ls commands/ agents/ skills/` (repo root), 2026-09-12
- `.echo/research/adopt-echo-plugin-to-codex.md` (prior session's research, cited for
  continuity on the hooks-lifecycle gap and the now-corrected Skills-directory claim; not
  re-verified in full here except where explicitly noted)
