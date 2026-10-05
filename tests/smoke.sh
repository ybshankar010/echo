#!/usr/bin/env bash
# End-to-end smoke test for echo on a fresh temp git repo.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$REPO/bin"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

cd "$T"
git init -q
git config user.email t@t.co
git config user.name t

echo "== init =="
"$BIN/echo-stage" init --ticket FEAT-3816 --title "smoke"

echo "== next blocks (gate pending) =="
if "$BIN/echo-stage" next; then echo "FAIL: next should block"; exit 1; fi

echo "== approve + next -> spec =="
"$BIN/echo-stage" approve
"$BIN/echo-stage" next | grep -q "advanced:spec"

echo "== artifacts are ticket-scoped =="
"$BIN/echo-stage" set-artifact --stage spec | grep -q ".echo/artifacts/FEAT-3816/spec.md"
test -d .echo/artifacts/FEAT-3816

echo "== install commit-msg hook =="
"$BIN/echo-install-hooks"

echo "== verify (passing) writes artifact =="
"$BIN/echo-verify" -- true
test -f .echo/verify/FEAT-3816.md

echo "== ship dry-run enforces ticket =="
"$BIN/echo-git" ship -m "smoke ship" --desc smoke --dry-run | grep -q "Ticket: FEAT-3816"

echo "== build stage assets present =="
test -f "$REPO/commands/build.md"
test -f "$REPO/agents/builder.md"
test -f "$REPO/agents/critic.md"

echo "== research assets present =="
test -f "$REPO/commands/research.md"
test -f "$REPO/agents/researcher.md"
test -f "$REPO/skills/research-template/SKILL.md"

echo "== address-review assets present =="
test -f "$REPO/commands/address-review.md"
test -x "$BIN/echo-review-comments"
test -x "$BIN/echo-review-pr"
test -f "$REPO/skills/address-review/SKILL.md"

echo "== review-comments fetch fails open with no PR =="
"$BIN/echo-review-comments" fetch --ticket FEAT-3816 | grep -q . && { echo "FAIL: fetch should print nothing with no PR"; exit 1; } || true

echo "== research-path resolves (topic + ticket) =="
"$BIN/echo-stage" research-path --topic "smoke topic" | grep -q ".echo/research/smoke-topic.md"
"$BIN/echo-stage" research-path --ticket FEAT-3816 | grep -q ".echo/artifacts/FEAT-3816/research.md"

echo "== flow orchestrator present + gate-mode works =="
test -f "$REPO/commands/flow.md"
test "$("$BIN/echo-stage" gate-mode --stage plan)" = "stop"
test "$("$BIN/echo-stage" gate-mode --stage spec)" = "auto"

echo "== jira comment gate round trip (needed -> done -> needed) =="
test "$("$BIN/echo-stage" comment-needed --event stage:spec)" = "post FEAT-3816"
"$BIN/echo-stage" comment-done --event stage:spec
test "$("$BIN/echo-stage" comment-needed --event stage:spec)" = "skip"
test -f .echo/jira/FEAT-3816.json

echo "== watch run fails open with no PR and writes a skipped artifact =="
"$BIN/echo-watch" run --ticket FEAT-3816
test -f .echo/verify/FEAT-3816-ci.md
grep -q "result: skipped" .echo/verify/FEAT-3816-ci.md

echo "== review dir is created by ensure_dirs =="
PYTHONPATH="$REPO/lib" python3 -c "import echo_common as ec; ec.ensure_dirs('$T'); import os,sys; sys.exit(0 if os.path.isdir(ec.review_dir('$T')) else 1)"

echo "== codex: AGENTS.md is a symlink to CLAUDE.md =="
test -L "$REPO/AGENTS.md"
test "$(readlink "$REPO/AGENTS.md")" = "CLAUDE.md"
diff <(cat "$REPO/AGENTS.md") "$REPO/CLAUDE.md" >/dev/null

echo "== codex: CLAUDE.md has the Codex how-to with substance =="
grep -q "Using echo from OpenAI Codex" "$REPO/CLAUDE.md"
grep -q "echo-stage" "$REPO/CLAUDE.md"
grep -q "echo-verify" "$REPO/CLAUDE.md"
grep -q "echo-plan-guard" "$REPO/CLAUDE.md"
grep -q "echo-verify-gate" "$REPO/CLAUDE.md"
grep -qi "advisory" "$REPO/CLAUDE.md"
# no-Jira/no-MCP note, scoped to the new section so it can't pass on the pre-existing
# "Jira ticket id" policy text at CLAUDE.md:19 (a whole-file `grep jira` is a false positive):
sed -n '/## Using echo from OpenAI Codex/,$p' "$REPO/CLAUDE.md" | grep -qi "atlassian mcp"

echo "== codex phase2: command skills present =="
for n in flow research intent spec plan build verify review ship status approve next watch address-review; do
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

echo "== ste-writing skill present and mirrored =="
test -f "$REPO/skills/ste-writing/SKILL.md"
grep -q "^name:" "$REPO/skills/ste-writing/SKILL.md"
grep -q "^description:" "$REPO/skills/ste-writing/SKILL.md"
test -e "$REPO/.agents/skills/ste-writing/SKILL.md"

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

echo "== codex phase2: installer present, executable, valid, dry-run clean =="
test -x "$REPO/codex-install.sh"
bash -n "$REPO/codex-install.sh"
AGENTS_SKILLS_DIR="$T/askills" CODEX_AGENTS_DIR="$T/cagents" "$REPO/codex-install.sh" --dry-run >/dev/null
test ! -e "$T/askills"   # dry-run must not create anything

echo "== checklist: parse, count, check-next on a fixture plan =="
mkdir -p "$T/.echo/artifacts/FEAT-3816"
printf '## Order of work\n- [ ] 1. first\n- [ ] 2. second\n\n## Proof\n- [ ] not counted\n' \
  > "$T/.echo/artifacts/FEAT-3816/plan.md"
"$BIN/echo-stage" set-artifact --stage plan >/dev/null
"$BIN/echo-stage" checklist | grep -q "checklist: 0/2 done"     # Proof checkbox excluded
"$BIN/echo-stage" check-next | grep -q "checked: 1"
"$BIN/echo-stage" checklist | grep -q "checklist: 1/2 done"
"$BIN/echo-stage" check --index 2 >/dev/null
"$BIN/echo-stage" checklist | grep -q "checklist: 2/2 done"
grep -q -- "- \[x\] 1. first" "$T/.echo/artifacts/FEAT-3816/plan.md"   # text preserved, marker set

echo "ALL SMOKE CHECKS PASSED"
