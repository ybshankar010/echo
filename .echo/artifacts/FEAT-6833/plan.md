# Plan: Codex compatibility Phase 2 (commands to Skills, agents to agents.*)

- **Ticket:** FEAT-6833
- **Stage:** Build (kickoff)
- **Derived from:** `.echo/artifacts/FEAT-6833/spec.md`
- **Status:** draft (awaiting `/echo:approve`)

## Files that change (all additive; nothing under commands/agents/skills/hooks/bin/lib is edited)
- **13 command Skills** - `.agents/skills/echo-<name>/SKILL.md` for name in:
  `flow, research, intent, spec, plan, build, verify, review, ship, status, approve, next, watch`
  (all `commands/*.md` except `install-hooks`).
- **5 agent TOMLs** - `.codex/agents/<name>.toml` for: `builder, critic, reviewer, verifier, researcher`.
- **4 template skills discoverable** - `.agents/skills/<template>` symlink -> `../../skills/<template>`
  for: `intent-template, plan-template, research-template, spec-template` (copy only if a symlink
  cannot be created).
- **Known-limitations doc** - `.agents/skills/README.md`.
- **`tests/smoke.sh`** (edit) - append a `$REPO`-qualified codex-phase2 block before the final
  `echo "ALL SMOKE CHECKS PASSED"`.
- **`README.md`** (edit) - extend the Codex pointer to mention the Skills + agents + limitations doc.

## Authoring templates (build to these)
### SKILL.md (each command skill), no em dashes:
```
---
name: echo-<name>
description: <one line: when to use this skill, phrased so Codex can auto-trigger>
---

# echo <name> (Codex)

Codex port of echo's `/echo:<name>` command. It drives the same loop through the stdlib
`bin/echo-*` CLIs (unchanged).

## Arguments
Skills have no structured arguments. Read the ticket id (`[A-Z]+-[0-9]+`) and any goal text
from what the user typed; never fabricate a ticket.

## Steps
<the real steps adapted from commands/<name>.md, calling bin/echo-* exactly as that command does>

## Under Codex
Gates are advisory and orchestration is prose-driven. See `.agents/skills/README.md` for the
Known limitations before relying on this.
```
Adapt each body faithfully from the corresponding `commands/<name>.md` (read each). Where the
Claude Code command spawns a subagent via the Task tool, the Skill body instead asks Codex in
prose to delegate to the matching role agent (`.codex/agents/<role>.toml`), and points to the
limitations doc. Where it posts Jira comments, note that is Claude-only (skip on Codex).

### `.codex/agents/<name>.toml` (each agent), no em dashes:
```
name = "<name>"
description = "<from agents/<name>.md description>"
model = "<opus|sonnet as in agents/<name>.md; omit if none>"
# Report-only roles (critic, reviewer, verifier): read-only, never edit.
sandbox_mode = "read-only"   # builder: omit or a write-capable mode; researcher: as needed
developer_instructions = """
<the role prompt from the body of agents/<name>.md, adapted to Codex>
Never edit files; report only.   # (critic/reviewer/verifier only)
"""
```
builder: no read-only sandbox (it edits). verifier: needs to run tests; add a comment that Codex
may not express "execute but not write", so read-only is a best-effort compromise, re-check live.
researcher: add a comment that whether a spawned Codex agent gets web tools is unverified.

### `.agents/skills/README.md` (limitations doc) MUST contain these literal strings:
`prose-driven`, `not enforced by Codex`, `no structured arguments`, `advisory`, `unverified`
(researcher web tools), `install-hooks` (N/A note), `not verified in a live Codex session`.

### smoke.sh block (insert before the final ALL SMOKE CHECKS PASSED line), all `$REPO`-qualified:
```
echo "== codex phase2: command skills present =="
for n in flow research intent spec plan build verify review ship status approve next watch; do
  test -f "$REPO/.agents/skills/echo-$n/SKILL.md"
  grep -q "^name:" "$REPO/.agents/skills/echo-$n/SKILL.md"
  grep -q "^description:" "$REPO/.agents/skills/echo-$n/SKILL.md"
done

echo "== codex phase2: agent tomls present =="
for a in builder critic reviewer verifier researcher; do
  test -f "$REPO/.codex/agents/$a.toml"
  grep -q "name" "$REPO/.codex/agents/$a.toml"
  grep -q "description" "$REPO/.codex/agents/$a.toml"
  grep -q "developer_instructions" "$REPO/.codex/agents/$a.toml"
done
for a in critic reviewer verifier; do
  grep -qiE "never edit|read-only" "$REPO/.codex/agents/$a.toml"
done

echo "== codex phase2: template skills discoverable =="
for t in intent-template plan-template research-template spec-template; do
  test -e "$REPO/.agents/skills/$t/SKILL.md"
done

echo "== codex phase2: limitations doc has required substance =="
R="$REPO/.agents/skills/README.md"; test -f "$R"
for s in "prose-driven" "not enforced by Codex" "no structured arguments" "advisory" "unverified" "install-hooks" "not verified in a live Codex session"; do
  grep -qi "$s" "$R"
done

echo "== codex phase2: README points to Skills + limitations =="
grep -qi "skill" "$REPO/README.md"
grep -qi "known limitations" "$REPO/README.md"

echo "== codex phase2: Claude plugin manifests still valid (compat) =="
python3 -c "import json,sys; json.load(open('$REPO/.claude-plugin/plugin.json')); json.load(open('$REPO/.claude-plugin/marketplace.json'))"
```

## Order of work
0. `mkdir -p .agents/skills .codex/agents` (create the two Codex dirs before writing into them).
1. `.agents/skills/README.md` (limitations doc) with all required literal strings. (foundation)
2. The 13 `.agents/skills/echo-<name>/SKILL.md` (read each `commands/<name>.md` and adapt).
3. The 5 `.codex/agents/<name>.toml` (read each `agents/<name>.md` and carry the body into
   `developer_instructions`).
4. The 4 template symlinks `.agents/skills/<template>` -> `../../skills/<template>` (copy if symlink fails).
5. Append the smoke block; extend `README.md`.
6. Run the full Proof; fix content (not tests) until green.

## Risks
- **Authoring against unverified runtime:** none of this can be Codex-run here. Mitigation: author
  to verified static formats only; the limitations doc states the boundary; smoke checks structure,
  not Codex behavior.
- **Symlink template dirs not resolved by the smoke `test -e`:** a relative dir symlink
  `.agents/skills/<t>` -> `../../skills/<t>` resolves on disk; `test -e` follows it. If creation
  fails (e.g. FS), fall back to copying the dir. Mitigation in req/step 4.
- **em dashes creeping into 13+ generated files:** Mitigation: Proof greps for em dashes across all
  new files.
- **Accidental edit to the Claude Code surface:** Mitigation: Proof asserts the changed-path set
  excludes commands/agents/skills/hooks/bin/lib.
- **`grep -q "name"` matching loosely in tomls:** acceptable - the field is required and present;
  the check confirms presence, and false-positive risk is negligible for these authored files.

## Proof (runnable; this is what Test runs)
1. All 13 `.agents/skills/echo-<name>/SKILL.md` exist with `name:` and `description:` frontmatter.
2. All 5 `.codex/agents/<name>.toml` exist with `name`, `description`, `developer_instructions`;
   critic/reviewer/verifier contain `never edit` or `read-only`.
3. The 4 template skills are reachable at `.agents/skills/<template>/SKILL.md`.
4. `.agents/skills/README.md` contains all 7 required literal strings (AC4 list).
5. `python3 -m py_compile lib/echo_common.py bin/echo-*` -> exit 0 (core unchanged).
6. `python3 -m pytest tests/test_echo.py -q` -> 62 passed (none weakened).
7. `bash tests/smoke.sh` -> ALL SMOKE CHECKS PASSED including the new codex-phase2 block.
8. Changed-path scope is exactly the allowed set (runnable):
   `git status --porcelain | awk '{print $2}' | grep -vE '^(\.agents/|\.codex/|tests/smoke\.sh|README\.md|\.echo/)'`
   prints nothing (empty = pass). In particular nothing under
   `commands/|agents/|skills/|hooks/|bin/|lib/|\.claude-plugin/` appears.
9. `grep -rn "—" .agents/ .codex/ README.md` finds no em dashes newly added by this build.
10. README content: `grep -qi "skill" README.md && grep -qi "known limitations" README.md`
    (the Codex section now points to the Skills/agents and the limitations doc), so the README edit
    is enforced, not optional.
11. Claude compatibility (echo is a Claude plugin first):
    - `git status --porcelain` shows no modification under `.claude-plugin/ commands/ agents/
      skills/ hooks/ bin/ lib/` (subset of Proof 8, called out explicitly).
    - `python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json'))"`
      exits 0 (manifests unchanged and valid).
    - each `.agents/skills/<template>` resolves to the existing `skills/<template>` (symlink target),
      so no new/duplicate skill identity is introduced.
    - Manual (cannot run from a script): `/reload-plugins` still loads echo with unchanged
      command/agent/skill counts. Flag this as the user's confirm step.

## Definition of done
- All Proof checks pass; existing 62 tests + smoke stay green; no `bin/lib` or Claude Code changes.
- 13 command Skills, 5 agent TOMLs, 4 discoverable template skills, and the limitations doc exist
  and are well-formed to the verified formats.
- The limitations doc honestly states every unverified boundary (orchestration prose-driven, tool
  restrictions not enforced, no structured args, gates advisory, researcher web tools unverified,
  install-hooks N/A, not verified in a live Codex session).
- README points a Codex user to the Skills, agents, and limitations doc.
