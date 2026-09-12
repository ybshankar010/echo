# Spec: Codex compatibility Phase 2 (commands to Skills, agents to agents.*)

- **Ticket:** FEAT-6833
- **Stage:** Design
- **Derived from:** `.echo/artifacts/FEAT-6833/intent.md`
- **Status:** draft (awaiting `/echo:approve`)

## Overview
Author Codex-native siblings for echo's workflow surface, to the primary-source-verified formats
in `.echo/research/codex-phase2-skills-and-agents-formats.md`, without touching the Claude Code
plugin or the `bin/`/`lib/` core. Each `commands/*.md` (except `install-hooks`) becomes a Codex
Skill at `.agents/skills/echo-<name>/SKILL.md`; each `agents/*.md` becomes a `.codex/agents/<name>.toml`;
the 4 template skills are made Codex-discoverable; and a single "Known limitations (Codex)"
document states the verified/unverified boundary in grep-able language. Orchestration is
documented as prose-driven natural-language delegation, because the cross-agent spawn primitive is
UNVERIFIED; nothing is coded against a guessed `spawn_agent` schema.

Ordering note (reconciling the research): the Phase 2 research recommended verifying the
cross-agent invocation mechanism hands-on before writing this spec. No Codex CLI is installed in
this environment, so that verification is consciously deferred to a follow-up; this spec therefore
authors artifacts to the verified static formats only and treats orchestration and runtime
behavior as explicitly unverified, rather than blocking Phase 2 entirely.

## Requirements
Each is testable and traces to the intent.

1. **Command Skills.** For each of these 13 commands (all 14 `commands/*.md` except `install-hooks`),
   create `.agents/skills/echo-<name>/SKILL.md`
   with YAML frontmatter `name: echo-<name>` and a `description:` (one line stating when the skill
   applies), followed by a Markdown body adapted from the command: flow, research, intent, spec,
   plan, build, verify, review, ship, status, approve, next, watch. The body MUST (a) instruct the
   reader to extract the ticket id / goal from the user's free-text prompt (no `$ARGUMENTS` under
   Skills), and (b) drive the loop through the stdlib `bin/echo-*` CLIs (same determinism as the
   Claude Code commands). `install-hooks` is intentionally NOT ported (no Codex hook surface); it
   is listed in the limitations doc instead.
2. **Agent TOMLs.** For each of the 5 agents create `.codex/agents/<name>.toml` (builder, critic,
   reviewer, verifier, researcher) with required keys `name`, `description`, `developer_instructions`
   (the role prompt, carried from the agent's `.md` body), and `model` where the source names one.
   The report-only roles (critic, reviewer, verifier) MUST carry an explicit "never edit files"
   sentence in `developer_instructions` and set `sandbox_mode = "read-only"` where that does not
   break the role. The verifier needs to run tests: document (in the toml as a comment and in the
   limitations doc) that Codex may not express "execute but not write" granularity, so its sandbox
   setting is a best-effort compromise.
3. **Template skills discoverable by Codex.** Make the 4 `skills/*-template` reachable under
   `.agents/skills/` (their minimal `name`+`description` schema already works under Codex). Default:
   symlink each template directory into `.agents/skills/` (single source, matches Phase 1); if a
   symlinked directory is not discovered by Codex, fall back to copying (decided at build via the
   check in req 6). The originals under `skills/` are untouched.
4. **Known-limitations doc (grep-able).** Create `.agents/skills/README.md` (or a clearly named doc
   under `.agents/skills/`) with a `## Known limitations (Codex)` heading that states, in literal
   text a grep can assert, every one of these: orchestration is "prose-driven" (no verified
   cross-agent spawn primitive); report-only agent restrictions are "not enforced by Codex" (no
   per-agent tool allowlist); Skills have "no structured arguments" (the ticket/goal is parsed from
   the prompt); gates are "advisory"; the `researcher` role's web-tool access under a spawned Codex
   agent is "unverified"; `install-hooks` has no Codex equivalent ("install-hooks" N/A); and none of
   this is "not verified in a live Codex session" yet. Every quoted phrase above is a required
   literal that acceptance criterion 4 greps for, so no required statement can be silently dropped.
5. **No Claude Code regression.** No change under `commands/`, `agents/`, `skills/` (originals),
   `hooks/`, `bin/`, `lib/`. Existing 62 unit tests and the smoke suite stay green.
6. **Smoke coverage.** Add `$REPO`-qualified smoke checks that: each expected
   `.agents/skills/echo-<name>/SKILL.md` exists and its first lines contain `name:` and
   `description:`; each `.codex/agents/<name>.toml` exists and contains `name`, `description`,
   `developer_instructions`; the report-only tomls contain a no-edit phrase; the template skills
   are reachable under `.agents/skills/`; and the limitations doc contains the required literal
   strings. If symlinked template dirs are not resolvable, the build switches to copies and the
   check still passes.

7. **Claude plugin stays valid (echo is a Claude Code plugin first).** The Codex additions are
   purely additive and must not break Claude compatibility: `.claude-plugin/plugin.json` and
   `.claude-plugin/marketplace.json` are unchanged and remain valid JSON; no file under
   `.claude-plugin/`, `commands/`, `agents/`, `skills/`, `hooks/`, `bin/`, `lib/` is modified; and
   the new `.agents/skills/` template entries are symlinks to the SAME `skills/*-template` dirs (not
   new/duplicate skill identities), so Claude Code's plugin loader sees no new or changed skills.
   Because Claude Code loads the plugin's declared `skills/`/`commands/`/`agents/`/`hooks/` (per
   `plugin.json`), not `.agents/` or `.codex/`, those Codex dirs are inert to Claude Code. A
   `/reload-plugins` must still load echo cleanly with unchanged command/agent/skill counts (a
   manual verify step, since the harness command cannot be run from a script).

## Design
- **New files (all additive):**
  - `.agents/skills/echo-<name>/SKILL.md` x13.
  - `.agents/skills/<template>/` x4 (symlink or copy of the existing `skills/*-template`).
  - `.agents/skills/README.md` (the Known-limitations doc).
  - `.codex/agents/<name>.toml` x5.
  - `tests/smoke.sh` (edit) - append a `$REPO`-qualified codex-phase2 block before the final line.
  - `README.md` (edit) - extend the Codex pointer to mention the Skills + agents and link the
    limitations doc.
- **SKILL.md body pattern** (consistent across the 13): a short intro, "How to invoke" (type the
  request; Codex may auto-trigger on the description or the user runs `/skills`), "Arguments"
  (extract ticket id/goal from the prompt), "Steps" (the command's real steps, calling `bin/echo-*`),
  and a "Under Codex" note pointing to the limitations doc for gates/orchestration caveats.
- **Reuse:** the SKILL.md schema echo already uses (`skills/*-template/SKILL.md`); the smoke-test
  harness and its `$REPO` convention; the unchanged `bin/echo-*` CLIs the bodies call.
- **Key decisions (resolving intent open questions):**
  - Port scope: all commands except `install-hooks` (13 skills); `install-hooks` documented as N/A.
  - Template placement: symlink by default; copy fallback only if the symlink cannot be created on
    the filesystem. (No live Codex here, so "does Codex discover it" is not checked at build; the
    smoke test only asserts the link resolves on disk.)
  - Agent TOML dir `.codex/agents/`, Skills dir `.agents/skills/` (two dirs, per the docs). No Codex
    is installed here to re-check, so the build authors to the documented paths and records the
    path-churn risk (openai/codex#15972) in the limitations doc as a re-verify-on-your-Codex item.
  - Orchestration + tool-allowlist + runtime: documented as unverified, never coded as if working.

## Flagged concerns
- **Unverifiable at build time (integrity/honesty):** Skills triggering, subagent spawning, and the
  `.agents/skills` search path cannot be tested without a live Codex CLI. Mitigation: author to
  verified static formats; the limitations doc states plainly what is unverified; a live-Codex pass
  is a named follow-up, not a claim of done.
- **Orchestration may not work as written:** the flow/build/plan Skills instruct Codex in prose to
  delegate to agent roles, but no verified spawn primitive backs that. Mitigation: the bodies use
  natural-language delegation (the only documented mechanism) and the limitations doc says so.
- **Report-only guarantee weakened:** critic/reviewer/verifier "never edit" is prose +
  `sandbox_mode`, not an enforced allowlist. Mitigation: stated in each toml and the limitations doc.
- **Researcher tool ACCESS gap (not just restriction):** whether a spawned Codex agent even gets
  WebSearch/WebFetch-equivalent tools is not enumerated in the docs (research mapping table). So the
  researcher toml documenting "needs web access" is aspirational under Codex until verified live.
  Mitigation: called out in the researcher toml and the limitations doc as unverified.
- **`sandbox_mode` value unconfirmed:** the research confirmed the field exists but not its exact
  enum strings; `"read-only"` is a best-effort value to re-check against the installed Codex.
- **Path churn:** the Skills dir moved once recently. Mitigation: limitations doc says to re-check
  against the installed Codex version; smoke asserts the paths this build authored.
- **Compliance:** no third-party deps; no em dashes in new prose; Jira/ticket policy unaffected;
  no secrets.

## Non-goals
- Runtime verification in a live Codex session (required follow-up; no Codex installed here).
- The deprecated `~/.codex/prompts/` custom-prompts path.
- Any Codex-native gate/hook enforcement (gates stay advisory, per Phase 1).
- Coding against an unverified `spawn_agent`/`send_message` tool schema.
- Changing the Claude Code `commands/`, `agents/`, `skills/`, `hooks/`, `bin/`, `lib/`.
- Wiring Atlassian MCP for Codex.

## Acceptance criteria
All file checks are `$REPO`-qualified (smoke.sh runs in a temp repo).
1. For each of the 13 names, `test -f "$REPO/.agents/skills/echo-<name>/SKILL.md"` and its head
   contains `name:` and `description:`.
2. For each of the 5 agents, `test -f "$REPO/.codex/agents/<name>.toml"` and it contains `name`,
   `description`, `developer_instructions`; the critic/reviewer/verifier tomls contain a no-edit
   phrase (grep for e.g. `never edit` / `read-only`).
3. The 4 template skills are reachable under `$REPO/.agents/skills/` (symlink resolves, or a real
   dir exists) and each has a `SKILL.md`.
4. `$REPO/.agents/skills/README.md` exists and `grep` finds every required literal string:
   `prose-driven`, `not enforced by Codex`, `no structured arguments`, `advisory`, `unverified`
   (the researcher web-tool note), `install-hooks`, and `not verified in a live Codex session`.
5. `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0 (core unchanged).
6. `python3 -m pytest tests/test_echo.py -q` stays green (62 passed, none weakened).
7. `bash tests/smoke.sh` exits 0 including the new codex-phase2 block.
8. Every changed path (`git status --porcelain`, including untracked) lies under `.agents/`,
   `.codex/`, `tests/smoke.sh`, `README.md`, or `.echo/` - and nothing under `commands/`, `agents/`,
   `skills/`, `hooks/`, `bin/`, `lib/` is modified (assert the complement is empty).
9. No em dashes in the new prose (`SKILL.md` files, tomls, README addition, limitations doc).
10. Claude compatibility: `git status --porcelain` shows NO modification under `.claude-plugin/`,
    `commands/`, `agents/`, `skills/`, `hooks/`, `bin/`, `lib/`; `python3 -c "import json;
    json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json'))"`
    exits 0 (manifests still valid JSON); the 4 `.agents/skills/<template>` entries resolve to the
    existing `skills/<template>` dirs. Manual: `/reload-plugins` still loads echo with unchanged counts.
