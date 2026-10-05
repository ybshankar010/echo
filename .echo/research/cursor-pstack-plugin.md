# Research: the Cursor plugin "pstack"

Question: what is the Cursor plugin `pstack`, how is it structured, and what does it tell us about the Cursor plugin model (and a possible future Cursor port of echo)?

Source repo: GitHub `cursor/plugins`, directory `pstack`, read at commit `be432a96ed36e48d05f44bf375864355f62263f9` via the GitHub MCP tool (owner=cursor, repo=plugins). Every claim below cites a file path within that repo (relative to `pstack/`) or the fetched README/manifest. Inference is labelled.

---

## 1. What pstack is

pstack is a Cursor plugin that packages one engineer's (Lauren Tan / "poteto", React core team, ex-Meta/Netflix, at Cursor) day-to-day rigorous-engineering workflow into reusable agent skills, subagents, and playbooks. Its stated purpose, from the manifest, is: "if you want to go fast, go deep first. pstack helps you write less, but higher quality code. rigorous agent workflows you can parallelize with confidence." (`.cursor-plugin/plugin.json`, `description`). The README frames it as a reaction to "ai writes too much slop code": the goal is "not to maximize loc, in fact it's the opposite" and it "turns cursor into a real engineering team" so you can "start multiple agents up with `poteto-mode` and trust that they'll apply rigorous engineering principles" (`README.md`, intro). In short, it is an opinionated agent-behavior layer (a "style") built around a single entry-point mode, 23 one-rule engineering principles, task-specific playbooks, and multi-model/parallel subagent workflows, all aimed at correctness and verification over volume.

## 2. The `.cursor-plugin` manifest

Cursor plugins carry a manifest at `.cursor-plugin/plugin.json` (a directory, not a single dotfile). pstack's manifest (`.cursor-plugin/plugin.json`) declares:

- `name`: `pstack`; `displayName`: `pstack`
- `version`: `0.15.2`
- `description`: the "go deep first" tagline (quoted above)
- `author`: `{ "name": "Lauren Tan" }`
- `homepage`: `https://github.com/cursor/plugins/tree/main/pstack`
- `repository`: `https://github.com/cursor/plugins`
- `license`: `MIT`
- `logo`: `assets/logo.png`
- `keywords`: `["pstack", "poteto-mode", "workflow", "principles", "agent-style", "subagents", "unslop"]`
- `category`: `developer-tools`
- `tags`: `["workflow", "principles", "review", "planning"]`
- `skills`: `"./skills/"` (directory pointer)
- `agents`: `"./agents/"` (directory pointer)

What this tells us about the Cursor plugin format:
- A plugin registers component types by pointing the manifest at a directory. Here only two component types are registered as first-class: `skills` and `agents` (`.cursor-plugin/plugin.json`).
- There is NO `automations` key, NO `commands` key, and NO `hooks` key in the manifest. This is consistent with the README's note that the `automations/benny/` pack is "dormant" and "not registered as slash skills" (`README.md`, "automations" section) - inference: automations are set up per-project rather than registered by the plugin manifest.
- The manifest carries marketplace-style metadata (`displayName`, `logo`, `category`, `tags`, `keywords`, `homepage`), which suggests Cursor plugins are distributed through a gallery/registry. Inference, based on the presence of those fields plus the README install line `/add-plugin pstack` (`README.md`, "install").
- Skills double as slash commands. The README refers to skills as `/how`, `/interrogate`, `/setup-pstack`, etc., and the manifest exposes them via the `skills` dir, so a skill directory both defines an agent-invocable skill and a user-typable slash command. Inference from README usage examples cross-referenced with the `skills` pointer.

## 3. Components

Counts are from directory listings of `pstack/` at the pinned commit.

### `agents/` - 2 files (`agents/` listing)
Cursor "agents" here are subagent definitions (Markdown with YAML frontmatter: `name`, `description`, optional `is_background`) that a parent agent spawns via `subagent_type`.
- `agents/poteto-agent.md` - the routing target for `/poteto-mode` and "poteto's style". Frontmatter sets `is_background: true`. Its whole job is to read the `poteto-mode` skill's `SKILL.md` in full (including the inline principles index) before doing any work; it warns that substituting `generalPurpose` "skips that read and drifts" (`agents/poteto-agent.md`).
- `agents/comment-sicko.md` - a read-only "comment reviewer" persona (`subagent_type: "Comment Sicko"`) that hunts and flags comments for deletion, with a fixed keep-list (legal headers, external-dependency gotchas, lint suppressions with a real rule, public-API doc comments, RFC/issue links). It only reports and flags `MUST KILL`; it "never write[s] application code" (`agents/comment-sicko.md`). Usually invoked via the `no-comments` skill (`README.md`, subagents section).

### `skills/` - 47 directories, each a `SKILL.md` (`skills/` listing)
Cursor "skills" are Markdown instruction files (frontmatter `name`, `description`, plus flags like `disable-model-invocation`, `mode`, `icon`, `color`, `reminder`) that are both model-invocable and exposed as slash commands. They can reference sibling files (`references/`, `playbooks/`, `scripts/`) - e.g. `skills/poteto-mode/` contains `SKILL.md` plus `playbooks/`, `references/`, `scripts/` subdirs (`skills/poteto-mode/` listing).

The 47 split into two groups:
- 24 workflow/utility skills: `poteto-mode` (the entry point), `how`, `why`, `recall`, `blast-radius`, `architect`, `arena`, `swarm`, `interrogate`, `automate-me`, `make-bot-ui`, `setup-pstack`, `reflect`, `teach`, `tdd`, `no-comments`, `typescript-best-practices`, `figure-it-out`, `show-me-your-work`, `create-verification-skill`, `maintain-verification-skill`, `unslop`, `bro`, `technical-writing` (`README.md` "skills" table; `skills/` listing).
- 23 "principle" skills, one rule each, prefixed `principle-*` (e.g. `principle-laziness-protocol`, `principle-prove-it-works`, `principle-fix-root-causes`, `principle-type-system-discipline`, `principle-guard-the-context-window`). They are grouped core / architecture / verification / delegation / meta. `poteto-mode` indexes them inline and reads that index at task start; the standalone files exist "so other skills can reference a principle by name" (`README.md`, "principles"; the full index is in `skills/poteto-mode/SKILL.md`, "Principles").

Representative skill design (`skills/how/SKILL.md`): frontmatter `disable-model-invocation: true`; body is a numbered procedure that assesses complexity, spawns parallel read-only explorer subagents (default model `grok-4.6-fast-xhigh`) for complex questions or a single explainer (default `claude-fable-5-1-thinking-max`) for simple ones, then synthesizes and presents. This shows skills orchestrate subagents and encode multi-model routing.

The core `skills/poteto-mode/SKILL.md` is a "mode" skill (`mode: true`, `disable-model-invocation: true`, `reminder:` line). It defines: non-negotiable triggers (route to `how`/`architect`/`swarm`/`arena`/`interrogate`/`unslop`/`no-comments`/`technical-writing` etc. on matching conditions), the 23-principle index, an autonomy contract ("Just do it" for reversible work, "Always pause" for irreversible writes), subagent defaults (`run_in_background: true`, per-role model, file pointers not inlined context), reply-style rules (short declarative sentences, no long dashes, no mid-sentence colons), comment rules, and the playbook dispatch list.

### `skills/poteto-mode/playbooks/` - 23 files (`playbooks/` listing; README calls them "the twenty-three playbooks")
Playbooks are step lists for task shapes: `investigation`, `bug-fix`, `perf-issue`, `hillclimb`, `runtime-forensics`, `trace-forensics`, `feature`, `refactoring`, `prototype`, `visual-parity`, `authoring-a-skill`, `eval`, `babysit`, `shipping`, `autonomous-run`, `orchestrate`, `autopilot-full`, `autopilot-stack`, `session-pickup`, `pause-safely`, `multi-phase-plan`, `worktree-cleanup`, `opening-a-pr`. On invocation `poteto-mode` matches the task to a playbook and opens a todo list whose first items are the playbook's steps copied verbatim (`skills/poteto-mode/SKILL.md`, "Playbooks").

### `automations/` - 1 pack: `benny` (`automations/` listing)
Cursor "automations" are event-triggered agent workflows (e.g. a Slack trigger), created via Cursor's built-in `/automate`, not registered as slash skills. The `benny` pack contains `FOR_AGENTS.md` (setup intent the user points Cursor at), `README.md`, a `skills/` dir with three sub-skills (`setup-benny`, `triage-issue-reports`, `reproduce-and-fix-issues`), and `templates/` (`automations/benny/` listing). benny ships two automations that share one Slack issue channel: automation 1 triages each new report (classify bug/perf/feature/question, search tracker for duplicates, reply once with a `[benny:...]` marker) and automation 2 reproduces confirmed bugs through the real UI and may open a draft PR after before/after proof (`automations/benny/FOR_AGENTS.md`; `automations/benny/README.md`). Setup copies the pack into the target repo at `.cursor/automations/benny/`, enables pstack in the target's `.cursor/settings.json` for shared skills, and keeps user config outside the pack (`README.md` "automations"; `automations/benny/FOR_AGENTS.md`, "for the agent"). Its `SKILL.md` files are "direct automation instructions, not registered plugin skills" (`automations/benny/FOR_AGENTS.md`).

### `docs/` - 1 guide (`docs/` listing)
`docs/guide/` holds an 11-file ordered guide (`README.md` + `01-setup.md` through `10-recipes-and-pitfalls.md`) plus an `images/` dir (`docs/guide/` listing). The guide teaches the intended habit: "describe what you want and how you'll know it's done", let `/poteto-mode` pick a playbook and run skills, and read the evidence (`docs/guide/README.md`).

### `assets/` - 1 file
`assets/logo.png` (~361 KB), referenced by the manifest `logo` field (`assets/` listing; `.cursor-plugin/plugin.json`).

Also present at root: `LICENSE` (MIT), `.gitignore` (`node_modules/`, `.DS_Store`, `*.log`) (`.gitignore`).

## 4. How it works / how a user invokes it

Install and setup (`README.md` "install"/"get started"; `docs/guide/README.md`):
1. `/add-plugin pstack` to install.
2. `/setup-pstack` - pick a reasoning budget and which models fill each role.
3. `/poteto-mode` at the start of any task needing rigor.

Runtime flow (`skills/poteto-mode/SKILL.md`; `README.md` "usage"):
- `/poteto-mode` reads the request, matches it to one of the 23 playbooks, and opens a todo list seeded with that playbook's steps verbatim.
- It routes to other skills as steps fire (`how`, `architect`, `swarm`, `arena`, `interrogate`, `unslop`, `no-comments`, `tdd`, `technical-writing`, plus the principle skills).
- It is a "sticky mode": once entered it stays on across turns, applying itself when a playbook matches and staying out of the way otherwise; the user can opt out by saying so (`README.md` "usage"; frontmatter `mode: true` and `reminder:` in `skills/poteto-mode/SKILL.md`).
- Subagents: spawn with `subagent_type: "poteto-agent"`; defaults are `run_in_background: true`, per-role model selection, and passing file pointers rather than inlined context (`skills/poteto-mode/SKILL.md`, "Subagents"). Code delegates default to `grok-4.6-fast-xhigh`; hardest changes, prose, and judgment go to `claude-fable-5-1-thinking-max` (`README.md` "get started"; `skills/poteto-mode/SKILL.md`).
- Skills can also be invoked directly as slash commands, e.g. `/how do we cancel runs?`, `/interrogate review this pr` (`README.md` "skills").
- Autonomy contract: reversible work and external actions proceed without asking; irreversible writes (force-push to shared branches, deploys, data deletion, customer messages) always pause; session overrides like "going to bed" keep it running (`skills/poteto-mode/SKILL.md`, "Autonomy"). README notes it "works extremely well with cursor's `/loop` command" for multi-hour runs.

Config (`skills/setup-pstack/SKILL.md`): `/setup-pstack` writes `~/.cursor/rules/pstack-models.mdc`, an always-applied Cursor rule (`alwaysApply: true`) with a `# budget` line and one line per role mapping role -> model slug. Skills read this rule and fall back to defaults when a role line is absent. Budgets (`unlimited/large/medium/small`) set the reasoning-effort token on each model slug. This is the mechanism by which pstack does per-role, multi-model routing. Notably, config lives in a Cursor "rule" file (`.mdc` under `~/.cursor/rules/`), not in the plugin manifest.

Not bundled (dependencies on another plugin) (`README.md` "not shipped here"): `/deslop`, `control-cli`, `control-ui` ship in `cursor-team-kit`; `/create-skill` and a built-in `/babysit` are Cursor built-ins. pstack expects `cursor-team-kit` alongside it for the full set.

## 5. The Cursor plugin model in general (as evidenced by pstack)

Directory conventions evidenced by this repo:
- `.cursor-plugin/plugin.json` - the plugin manifest directory + JSON file (`.cursor-plugin/plugin.json`).
- `skills/<name>/SKILL.md` - a skill; frontmatter (`name`, `description`, optional `disable-model-invocation`, `mode`, `icon`, `color`, `reminder`); may hold `references/`, `playbooks/`, `scripts/` siblings. Skills are both model-invocable and slash commands (`skills/poteto-mode/SKILL.md`, `skills/how/SKILL.md`).
- `agents/<name>.md` - a subagent definition; frontmatter `name`, `description`, optional `is_background`; spawned via `subagent_type` (`agents/poteto-agent.md`, `agents/comment-sicko.md`).
- `automations/` - event-triggered workflow packs, set up per-project into `.cursor/automations/` via built-in `/automate`; NOT registered by the manifest (`automations/benny/FOR_AGENTS.md`; `README.md`).
- Project/user config via Cursor "rules": `.mdc` files with `alwaysApply` (project `.cursor/rules/` or user `~/.cursor/rules/`), and project settings via `.cursor/settings.json` with a `plugins` map, e.g. `{ "plugins": { "pstack": { "enabled": true } } }` (`skills/setup-pstack/SKILL.md`; `automations/benny/FOR_AGENTS.md`).
- Distribution/marketplace metadata in the manifest (`displayName`, `logo`, `category`, `tags`, `keywords`) and install via `/add-plugin` (`.cursor-plugin/plugin.json`; `README.md`).

Comparison to Claude Code and OpenAI Codex plugin models. The Cursor column is grounded in pstack; the Claude Code and Codex columns are general knowledge and are labelled inference where not directly evidenced by this repo.

| Concept | Cursor (from pstack) | Claude Code (inference) | OpenAI Codex (inference) |
|---|---|---|---|
| Manifest | `.cursor-plugin/plugin.json`, points at `skills/` and `agents/` dirs (`.cursor-plugin/plugin.json`) | `.claude-plugin/plugin.json` (plus `commands/`, `agents/`, `skills/`, `hooks/`) | No formal plugin manifest; `AGENTS.md` conventions, `.codex/` config |
| Slash commands | Skills double as slash commands (`README.md`) | Separate `commands/*.md` in addition to skills | Prompts/custom commands; less formalized |
| Skills | `skills/<name>/SKILL.md`, model- and user-invocable, can bundle references/playbooks/scripts (`skills/how/SKILL.md`) | `skills/<name>/SKILL.md` with `SKILL.md` + progressive-disclosure files | `.agents/skills` style skill files |
| Subagents | `agents/<name>.md`, spawned by `subagent_type`, `is_background` flag (`agents/poteto-agent.md`) | `agents/<name>.md` subagents with tool/model frontmatter | `.codex/agents` agent definitions |
| Hooks / lifecycle | Not seen in pstack (no `hooks` manifest key) | `hooks/hooks.json` wiring SessionStart/PreToolUse/Stop/etc. | Limited/none formalized |
| Event automations | `automations/` packs via built-in `/automate`, project-scoped, unregistered (`automations/benny/`) | No direct equivalent; closest is hooks | No direct equivalent |
| Config | Cursor rules (`.mdc`, `alwaysApply`) + `.cursor/settings.json` `plugins` map (`skills/setup-pstack/SKILL.md`) | `settings.json`, `CLAUDE.md` memory | `AGENTS.md`, `.codex/config` |
| Multi-model routing | First-class: per-role model slugs, budgets, panels of mixed models (`skills/setup-pstack/SKILL.md`) | Per-subagent `model` frontmatter; less panel-oriented (inference) | Single-provider by design (inference) |

Key structural contrasts (inference, cross-tool): Cursor and Claude Code share the same three core building blocks (skills, subagents, and a JSON manifest under a dot-directory), and both use `SKILL.md`. The visible differences in pstack are (a) Cursor folds slash commands into skills rather than a separate `commands/` type, (b) pstack shows no hooks mechanism (Claude Code's `hooks/hooks.json` is central to echo, see below), (c) Cursor has a distinct `automations/` concept for event-triggered flows, and (d) pstack leans hard into first-class multi-model routing (mixing Grok, Fable, Sol, Opus per role), which reflects Cursor's model-agnostic positioning ("use any model with pstack", `README.md`).

## 6. Relevance to echo (INFERENCE - short)

This whole section is inference about a hypothetical Cursor port of echo, based on comparing pstack's structure (sourced above) against echo's structure (from this repo's `CLAUDE.md`).

What maps cleanly:
- echo's `commands/*.md`, `agents/*.md`, and `skills/*/SKILL.md` map onto Cursor's `skills/` (commands+skills merge) and `agents/`. echo's maker-checker subagents (`critic`, `builder`, `reviewer`, `verifier`, `researcher`) map directly to Cursor `agents/<name>.md` spawned by `subagent_type`, much as pstack ships `poteto-agent` and `comment-sicko`.
- echo's staged SDLC loop (intent -> spec -> plan -> build -> test -> ship) resembles pstack's playbook-per-task-shape pattern; echo's `/echo:flow` is conceptually pstack's `/poteto-mode` (a single sticky entry point that sequences stages and routes to other skills).
- echo's ticket discipline and gate approvals could live in a Cursor rule (`.mdc`, `alwaysApply`) the way pstack stores its model config, plus `.cursor/settings.json` to enable the plugin.

What is a gap / risk:
- echo depends on hooks (`hooks/hooks.json` wiring SessionStart/PostCompact/PreToolUse/Stop/SessionEnd, including the plan-guard that blocks source edits until the plan gate is approved). pstack shows NO hooks mechanism in the Cursor plugin model. A Cursor port would need another enforcement path for the plan-guard and ticket gates (an always-applied rule plus skill-internal checks, or an automation), and gate enforcement would likely become advisory rather than a hard exit-code-2 block. This is the largest structural gap. (Inference: absence of hooks in pstack is not proof Cursor lacks them, only that pstack does not use them.)
- echo keeps determinism in Python `bin/`/`lib/` with state in `.echo/`. Cursor skills can bundle `scripts/` (pstack's `poteto-mode` has a `scripts/` dir), so echo's Python core could be carried along, but wiring it to run at fixed lifecycle points is the unsolved piece given the hooks gap.
- pstack's first-class multi-model routing is a feature echo does not currently exploit and could adopt in a Cursor port (e.g. critic vs builder on different models).

Net (inference): pstack is a strong template for the shape of a Cursor port of echo (entry-point mode + playbooks + subagents + rule-based config), but echo's hard, hook-enforced gates are the part that does not have a visible equivalent in pstack's evidence and would need rethinking.

---

## Sources (every pstack file read, by path relative to `pstack/`, at commit `be432a96`)

Read in full:
- `README.md`
- `.cursor-plugin/plugin.json`
- `agents/poteto-agent.md`
- `agents/comment-sicko.md`
- `skills/poteto-mode/SKILL.md`
- `skills/how/SKILL.md` (representative workflow skill)
- `skills/setup-pstack/SKILL.md`
- `automations/benny/FOR_AGENTS.md`
- `automations/benny/README.md`
- `docs/guide/README.md`
- `.gitignore`

Directory listings read (names/counts):
- `pstack/` (root)
- `.cursor-plugin/`
- `agents/`
- `skills/` (47 entries)
- `skills/poteto-mode/` and `skills/poteto-mode/playbooks/` (23 entries)
- `automations/` and `automations/benny/` and `automations/benny/skills/`
- `docs/` and `docs/guide/`
- `assets/`

Not opened in full (listed only, out of scope for this pass): the other 45 individual `skills/*/SKILL.md` files, the 23 `playbooks/*.md` bodies, `skills/poteto-mode/references/` and `scripts/`, `docs/guide/01-10*.md` bodies, benny sub-skill bodies, `LICENSE`, `assets/logo.png`.

Second pass (this update, same commit `be432a96`), read in full:
- All 23 `skills/principle-*/SKILL.md` files (enumerated below).
- `skills/poteto-mode/SKILL.md` re-read for the inline Principles index and trigger list.
- `skills/architect/SKILL.md`, `skills/interrogate/SKILL.md`, `skills/swarm/SKILL.md`, `skills/unslop/SKILL.md` (representative non-principle workflow skills).

---

## Design principles (pstack's 23, grounded)

Each principle is a `disable-model-invocation: true` skill (a slash command a person or another skill invokes by name, never auto-fired) whose body states one rule. The rule text below is condensed from each file's opening rule sentence; every entry cites its path (relative to `pstack/`) at commit `be432a96`. The one-line "when to apply" also appears in the poteto-mode index (`skills/poteto-mode/SKILL.md`, "Principles").

Core:
- **Laziness Protocol**: aim for the most result with the least code and complexity; prefer deletion and the smallest change that solves the problem. (`skills/principle-laziness-protocol/SKILL.md`)
- **Foundational Thinking**: get the data structures right before writing logic, and sequence scaffold before features so downstream code becomes obvious. (`skills/principle-foundational-thinking/SKILL.md`)
- **Redesign from First Principles**: when integrating a new requirement, redesign as if it had been foundational from day one instead of bolting it on. (`skills/principle-redesign-from-first-principles/SKILL.md`)
- **Attack the Premise**: when two or more fixes that share one premise have failed the same gate, suspect the premise, not the fixes (take a census of which actors hold the imbalance first). (`skills/principle-attack-the-premise/SKILL.md`)
- **Subtract Before You Add**: when evolving a system, remove complexity (dead code, redundant validators, stubs) first, then build on the simpler base. (`skills/principle-subtract-before-you-add/SKILL.md`)
- **Minimize Reader Load**: minimize the layers a reader must trace and the state they must hold; collapse one-caller wrappers and shrink mutable scope. (`skills/principle-minimize-reader-load/SKILL.md`)
- **Outcome-Oriented Execution**: optimize for the verifiable end state, not smooth intermediate states; planned, scoped, reversible breakage is fine, but verify at plan completion. (`skills/principle-outcome-oriented-execution/SKILL.md`)
- **Experience First**: when implementation convenience conflicts with user delight, choose delight; ship fewer polished features over more rough ones. (`skills/principle-experience-first/SKILL.md`)
- **Exhaust the Design Space**: when the right answer is not obvious, build 2-3 structurally distinct prototypes and compare side by side before committing. (`skills/principle-exhaust-the-design-space/SKILL.md`)
- **Build the Lever**: when the work is not trivial, build the tool that does or proves it (codemod, script, generator) instead of doing it by hand; the tool is the artifact a reviewer can rerun. (`skills/principle-build-the-lever/SKILL.md`)

Architecture:
- **Model the Domain**: encode the real domain in a data structure (state machine, typed model, registry, reducer) instead of scattering it across conditionals. (`skills/principle-model-the-domain/SKILL.md`)
- **Boundary Discipline**: place validation, type narrowing, and error handling at system boundaries; trust internal types and keep business logic in pure functions. (`skills/principle-boundary-discipline/SKILL.md`)
- **Type System Discipline**: use the type checker as a proof assistant: make illegal states unrepresentable, brand semantic primitives, parse external data at boundaries, exhaust variants. (`skills/principle-type-system-discipline/SKILL.md`)
- **Make Operations Idempotent**: design every state-mutating operation to converge to the same end state no matter how many times it runs or where a prior run crashed. (`skills/principle-make-operations-idempotent/SKILL.md`)
- **Migrate Callers Then Delete Legacy APIs**: when a new API is the right design, migrate all callers and delete the old API in the same wave instead of keeping compatibility layers. (`skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md`)
- **Separate Before Serializing Shared State**: when concurrent actors might share mutable state, eliminate the sharing first; serialize structurally only when one shared writer is a real invariant. (`skills/principle-separate-before-serializing-shared-state/SKILL.md`)

Verification:
- **Prove It Works**: verify every output against the real artifact (run it, read the actual value, inspect the diff), not a proxy, self-report, or "it compiles". (`skills/principle-prove-it-works/SKILL.md`)
- **Fix Root Causes**: when debugging, trace every symptom to its root cause and fix it there; reproduce first, ask why, do not add guards to silence a crash. (`skills/principle-fix-root-causes/SKILL.md`)
- **Sequence Work into Verifiable Units**: break work into small units that each end in a checkable state, verify each before the next, and order delivery so the sequence proves itself to a reviewer. (`skills/principle-sequence-verifiable-units/SKILL.md`)
- **Test Behavior, Not Implementation**: a test must call code the way its users do and assert the observed result against a literal value; if it would still pass when every imported function returns `undefined`, rewrite or delete it. (`skills/principle-test-behavior-not-implementation/SKILL.md`)

Delegation:
- **Guard the Context Window**: route bulk and verbose payloads to subagents and keep only summaries in the main thread; do not read what you will not use. (`skills/principle-guard-the-context-window/SKILL.md`)
- **Never Block on the Human**: on reversible work, proceed and present the result for after-the-fact course-correction; reserve confirmation for irreversible actions. (`skills/principle-never-block-on-the-human/SKILL.md`)

Meta:
- **Encode Lessons in Structure**: when you catch yourself writing the same instruction a second time, encode it as a lint rule, metadata flag, runtime check, or script instead of more text (and delete the instruction). (`skills/principle-encode-lessons-in-structure/SKILL.md`)

Philosophy. These 23 are one-rule engineering-behavior guardrails and coding-taste rules, not SDLC stages. Grounded in the files: each is a short skill that names one rule, one "why", a pattern, and a self-test, and cross-links sibling principles (e.g. Attack the Premise points at Build the Lever, Fix Root Causes, and Laziness Protocol). They shape how the agent decides and writes code (delete first, model the domain in types, verify against the real thing, do not block the human) rather than what phase the work is in. poteto-mode reads the index at task start and requires the agent to name each principle that shaped a decision and cite only principles whose leaf `SKILL.md` it read that session (`skills/poteto-mode/SKILL.md`, "Non-negotiables"), so the principles function as a checkable rubric layered over whichever playbook is running, never as gates that block progress.

## pstack skills vs echo - how they differ

(a) What a "skill" IS in each.
- pstack: a skill is a directory `skills/<name>/SKILL.md` with frontmatter (`name`, `description`, and flags like `disable-model-invocation`, `mode`, `icon`, `color`, `reminder`) that is both a slash command and, unless `disable-model-invocation: true`, an auto-triggerable behavior. It can carry `playbooks/`, `references/`, and `scripts/` siblings (`skills/poteto-mode/`). Principle skills are the pure-guidance flavor (rule text only, `disable-model-invocation: true`); workflow skills orchestrate subagents, e.g. `architect` runs a 5-phase Ground/Sketch/Agree/Implement/Scrap loop over the `arena` skill, `interrogate` fans out one reviewer per configured model then synthesizes a verdict, `swarm` runs a Frame/Fan-out/Aggregate/Report parallel-worker loop, `unslop` is a numbered find-and-fix pass over prose (`skills/architect/SKILL.md`, `skills/interrogate/SKILL.md`, `skills/swarm/SKILL.md`, `skills/unslop/SKILL.md`). The workflow skills' frontmatter is uniformly `name` + `description` + `disable-model-invocation: true`; the description carries the trigger phrases (e.g. "Use for /architect, 'architect this', 'design this'"). There is no separate args schema; arguments arrive as free text after the slash command (inference from the description fields and README usage like `/how do we cancel runs?`).
- echo: a "skill" is a much thinner thing. echo has only 4 skills, and all 4 are templates (`skills/{intent,spec,plan,research}-template`) that a command loads to know how to write that stage's artifact (confirmed by the skill list descriptions, e.g. "The structure and rules for writing an echo intent.md ... Use when running /echo:intent"). echo's real surface is `commands/*.md` (14: flow, research, status, intent, approve, next, spec, plan, build, verify, review, ship, watch, install-hooks) that orchestrate deterministic Python in `bin/echo-*` over shared logic in `lib/echo_common.py`, with subagents in `agents/*.md` (builder, critic, reviewer, verifier, researcher). So in pstack the skill IS the product; in echo the command + the `bin/` determinism is the product and skills are supporting templates. (Grounded in `commands/` and `agents/` listings, `lib/echo_common.py`, and the plugin skill list.)

(b) Philosophy.
- pstack shapes agent BEHAVIOR and output quality. Its enforcement is prose and Cursor rules: `poteto-mode` is a sticky `mode: true` skill that matches a task to one of 23 playbooks, seeds a todo list with the playbook's steps verbatim, and applies the 23 principles as a self-cited rubric. There is no persisted state machine and no hard gate; the autonomy contract only pauses on irreversible actions (force-push, deploy, data deletion, customer messages) and otherwise proceeds (`skills/poteto-mode/SKILL.md`, "Autonomy"; `skills/principle-never-block-on-the-human/SKILL.md`). Quality comes from maker-checker-style multi-model review (`interrogate`, `arena`) and the principle rubric, not from blocking.
- echo enforces a deterministic Plan -> Design -> Build -> Test -> Ship state machine with human gates. The stages are a hard-coded list `["intent","spec","plan","build","test","ship","done"]` with a per-stage approval gate (`lib/echo_common.py`, `STAGES`/`GATED_STAGES`/`new_item`). Enforcement is code, not prose: a PreToolUse plan-guard hook blocks Write/Edit until the plan gate is approved, and a Stop verify-gate hook blocks with exit code 2 (`hooks/hooks.json`; `CLAUDE.md`, "Hooks block with exit code 2"). Every work item carries a Jira ticket id (`TICKET_RE = [A-Z]+-[0-9]+`) enforced org-wide, and state plus artifacts are committed under `.echo/` (`state.json`, `config.json`, `artifacts/<TICKET>/...`). Gates fail open when no active item maps, but when they map they are hard. So pstack optimizes for unblocked, high-quality flow; echo optimizes for auditable, gated, ticketed progress. (The behavior-vs-state-machine contrast is inference drawn from the two sources side by side.)

(c) Concept mapping (inference where it crosses tools).

| Concept | pstack | echo |
|---|---|---|
| Entry point | `/poteto-mode`, a sticky `mode:true` skill that matches a playbook (`skills/poteto-mode/SKILL.md`) | `/echo:flow <ticket> <goal>`, an orchestrator over fixed stages (`commands/flow.md`, README) |
| Unit of work | a task-shape playbook, one of 23, matched at runtime (`skills/poteto-mode/SKILL.md`, "Playbooks") | one ticketed work item advanced through 6 stages (`lib/echo_common.py`, `STAGES`) |
| "Skill" | `SKILL.md` = slash command + (opt-in) auto-triggered behavior/principle (`skills/*/SKILL.md`) | a template a command loads to write an artifact (`skills/*-template`) |
| Real surface | `skills/` + `agents/` (+ playbooks/references/scripts) (`.cursor-plugin/plugin.json`) | `commands/` + deterministic `bin/` + `lib/` + `hooks/` (`CLAUDE.md`, "Architecture") |
| Quality mechanism | 23 one-rule principles read at task start; multi-model `interrogate`/`arena` (`skills/poteto-mode/SKILL.md`) | maker-checker `critic`/`reviewer` loop + verify (`README.md`, "Maker-checker") |
| Enforcement | prose + Cursor rules, advisory; no hooks (inference: no `hooks` key in `.cursor-plugin/plugin.json`) | hard hooks, exit 2: plan-guard, verify-gate; installable commit-msg gate (`hooks/hooks.json`) |
| Persisted state | none persisted by default; per-worker output files, `recall`/brain notes (`skills/swarm/SKILL.md`; README) | committed `.echo/` JSON state machine + per-ticket artifacts (`lib/echo_common.py`) |
| Human gates | autonomy contract: pause only on irreversible actions (`skills/principle-never-block-on-the-human/SKILL.md`) | explicit approval gate at every stage boundary (`lib/echo_common.py`, `gates`) |
| Config | `~/.cursor/rules/pstack-models.mdc` + `.cursor/settings.json` (`skills/setup-pstack/SKILL.md`) | `.echo/config.json` (`lib/echo_common.py`, `DEFAULT_CONFIG`) |
| Multi-model | first-class per-role model routing (grok/fable/sol/opus) (`skills/interrogate/SKILL.md`, `skills/swarm/SKILL.md`) | single-model subagents; no per-role routing (inference from `agents/*.md`) |
| Ticket policy | none observed | Jira `[A-Z]+-[0-9]+` required on branch/commit/PR (`CLAUDE.md`; `lib/echo_common.py`, `TICKET_RE`) |

(d) What each could borrow (inference).
- echo could borrow from pstack: a small library of one-rule principle skills that the `builder`, `critic`, and `reviewer` subagents read and must cite (behavior guardrails layered over echo's stages, not replacing them); first-class multi-model routing so `critic` and `builder` run on different models (pstack's `interrogate`/`swarm` pattern); and task-shape playbooks for non-SDLC work (bug-fix, perf, refactor) that do not fit the linear intent->ship loop.
- pstack could borrow from echo: a deterministic, committed state machine with hard gates for the moments where advisory prose is not enough (an approved-plan gate before code, a green-verify gate before "done"), a ticket-linkage discipline, and a persisted artifact trail (echo's `.echo/artifacts/<TICKET>/`) so work survives session restarts rather than living only in a todo list and brain notes.
