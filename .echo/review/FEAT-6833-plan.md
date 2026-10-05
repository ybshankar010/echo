# Critic review: FEAT-6833 plan vs spec

Verdict: no blocking gaps. Plan covers spec requirements 1-9 and acceptance criteria 1-9.

## Verified
- skills/ has 4 template skills plus address-review; the four .agents/skills/*-template are symlinks.
- echo-ship, echo-review, echo-address-review are real directories with SKILL.md. .agents/skills/ste-writing does not exist yet (new symlink is correct).
- commands/ship.md and address-review.md already name the Co-Authored-By trailer; review.md spawns the reviewer (lines 16, 33).
- plugin.json is 0.6.0. smoke.sh template loop is at lines 115-117. CLAUDE.md has the no-em-dash line (49).
- bin/echo-git, lib/, recap untouched; consistent with spec.

## Important (non-blocking)
1. skills/address-review/SKILL.md is a real skill that the address-review command loads and that governs Jira comment and reply prose. Neither spec nor plan mentions it. Decide: add the STE pointer there too, or note it as out of scope. Traces to spec Req 4.
2. README.md line ~119 says Codex ports are "the four template skills". After the change there are five skill dirs; step 5 should update that sentence, not only "name the skill". .agents/skills/README.md may also list skills; check it.
3. Proof 3 and Proof 6 only prove a string match. They do not prove the Co-Authored-By trailer and ticket prefix lines survive. Add a diff check that the edits are additions only (git diff --cached --numstat shows 0 deletions on those files).

## Nits
- Order-of-work step 8 is "Run Proof" as one checkbox for 9 checks; fine, but Proof step 8 (em dash) needs git add -A first. State that ordering in step 8.
- Step 2 says "Rules area"; skills/address-review and templates each have a "No em dashes" rule line. Name that as the insertion point.
- Spec Req 1 lists themes without "warnings and cautions" wording; plan adds it. Minor mismatch, harmless.
