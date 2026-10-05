Ticket: FEAT-6833
Stage: Design
Derived from: intent.md
Status: draft

# Write echo artifacts in Simplified Technical English

## Overview
Add a reusable `ste-writing` skill that states the full public ASD-STE100 writing rule set
in actionable form. Point every echo flow that writes prose at this skill: the four artifact
templates (intent, spec, plan, research), the ship and address-review flows that write commit
and PR text, and the review and recap prose. The skill is the single source of truth. This is
a prose and skill change. No `bin/` or `lib/` determinism changes.

## Requirements
1. A new skill `skills/ste-writing/SKILL.md` exists with `name:` and `description:`
   frontmatter, and its body states the full public ASD-STE100 writing rules in actionable
   form, grouped by theme (sentences, words, verbs, procedures, warnings, punctuation). The
   skill states the approved-word principles but does not reproduce the proprietary
   dictionary. (traces to intent: Proposed outcome; Decisions, full rule set)
2. The skill lists the scope boundary: apply STE to prose only, never to code, file paths,
   commands, ticket ids, or identifiers. (traces to intent: Constraints)
3. The four artifact template skills (`skills/intent-template`, `skills/spec-template`,
   `skills/plan-template`, `skills/research-template`) each reference `ste-writing` and tell
   the writer to apply STE to the artifact prose. (traces to intent: Proposed outcome)
4. The commit and PR prose follows STE: `commands/ship.md` and `commands/address-review.md`
   instruct that the `-m` descriptive prose uses STE, while the `TICKET: ` prefix, the
   `Ticket: <id>` body line, and the Co-Authored-By trailer stay exactly as policy requires.
   `bin/echo-git` builds the PR body from the same `-m` string plus the trailer, so writing
   the `-m` prose in STE is enough; `bin/echo-git` is not touched. The hardcoded followup
   message `address review comments` is already short and imperative, so it stays. (traces to
   intent: Decisions, commit/PR; Affected systems)
5. The review summary prose follows STE: `commands/review.md` tells the reviewer to write its
   summary in STE. The recap is deterministic output from `bin/echo-capture` f-strings, so it
   is out of scope (see Non-goals); the requirement does not touch `bin/`. (traces to intent:
   Proposed outcome)
6. The Codex mirrors stay consistent. The four `.agents/skills/*-template` mirrors are
   symlinks to `../../skills/*`, so the template edits reach Codex with no extra work. Add a
   new `.agents/skills/ste-writing` symlink to `../../skills/ste-writing` (a symlink, not a
   copy, so it never drifts). The Codex command skills `echo-ship`, `echo-review`, and
   `echo-address-review` are real directory copies, so each gets the same STE note as its
   `commands/*.md` source. (traces to intent: Affected systems)
7. The repo docs record the rule: `CLAUDE.md` Conventions names the STE rule with a pointer
   to the `ste-writing` skill, and `README.md` names the skill. (traces to intent: Affected
   systems)
8. The plugin version in `.claude-plugin/plugin.json` is bumped (minor; this is a new
   feature). (traces to intent: Affected systems)
9. No reviewer STE pass is added, and no STE checker is added to `bin/` or `lib/`. (traces to
   intent: Decisions, no pass now; Constraints, non-goal)

## Design
- `skills/ste-writing/SKILL.md` follows the shape of the existing template skills: `---`
  frontmatter with `name: ste-writing` and a one-line `description`, then a terse body. The
  body groups the public ASD-STE100 writing rules so a writer can apply them without the
  standard in hand. It names the dictionary as out of scope (proprietary) and states the
  approved-word principles (one word for one meaning, use the approved sense, avoid synonyms).
- Each artifact template gains one short line near its Rules section: "Write the prose in
  Simplified Technical English; load the `echo:ste-writing` skill." This mirrors how the
  templates already cross-reference, for example how `address-review.md` names
  `echo:plan-template`. The templates keep their existing structure and the no-em-dash rule.
- `commands/ship.md` and `commands/address-review.md` gain one line: write the commit message
  and PR description prose in STE (load `echo:ste-writing`), and keep the ticket prefix, the
  `Ticket: <id>` line, and the Co-Authored-By trailer unchanged. `bin/echo-git` is not
  touched; it only prepends the prefix and the trailer to the model-supplied prose, so the
  STE change is prose guidance in the command markdown, not determinism.
- Review: `commands/review.md` already spawns the reviewer; add the STE line to the reviewer
  prompt for the summary prose. Recap is deterministic (`bin/echo-capture` writes it from
  f-strings), so it stays out of scope; applying STE there would mean a `bin/` change, which
  is a non-goal.
- Codex parity: add the `.agents/skills/ste-writing` symlink to `../../skills/ste-writing`
  (matching the symlinked template mirrors). The template mirrors are already symlinks, so
  their edits need no Codex action. Edit the real copies `echo-ship`, `echo-review`, and
  `echo-address-review` to carry the STE note their `commands/*.md` sources carry.
- `CLAUDE.md` Conventions gains a one-line rule beside the no-em-dash rule. `README.md` adds
  `ste-writing` to the skill or feature list.

## Flagged concerns
- Copyright: the official ASD-STE100 dictionary is proprietary. Mitigation: the skill states
  the public writing rules and the word principles only, with a pointer to the standard, and
  does not reproduce the approved-word list. Not a security or privacy risk.
- Drift across sites: STE is named in several files (one skill, four templates, two command
  flows, two Codex mirrors, two doc files). Mitigation: the substance lives only in
  `ste-writing`; every other site is a one-line pointer, so there is one source to maintain.
  A deterministic doc-sync test is a non-goal (same reasoning as past echo features).
- Readability of echo itself: STE could make echo's own prose terse. Accepted: terse,
  consistent prose is the goal; the templates keep their required sections.

## Non-goals
- No reviewer STE pass and no STE grammar checker in `bin/` or `lib/`.
- No change to the loop state machine, the gates, or the Jira flow.
- No change to `bin/echo-git` message assembly (prefix and trailer stay as code).
- No STE applied to the recap: `bin/echo-capture` writes it deterministically from f-strings,
  and touching `bin/` is out of scope.
- No reproduction of the proprietary approved-word dictionary.

## Acceptance criteria
1. `test -f skills/ste-writing/SKILL.md` and it has `^name:` and `^description:` frontmatter;
   its body names ASD-STE100 and the scope boundary (prose only, not code or commands).
2. The four templates reference the skill:
   `grep -l "ste-writing" skills/intent-template/SKILL.md skills/spec-template/SKILL.md skills/plan-template/SKILL.md skills/research-template/SKILL.md`
   lists all four.
3. Commit/PR STE with policy intact:
   `grep -l "ste-writing" commands/ship.md commands/address-review.md` lists both, and those
   files still name the Co-Authored-By trailer and the ticket prefix.
4. Review prose: `grep -in "ste-writing\|Simplified Technical English" commands/review.md`
   matches.
5. Codex parity: `test -e .agents/skills/ste-writing/SKILL.md` (the new symlink resolves),
   and `grep -l "ste-writing" .agents/skills/echo-ship/SKILL.md .agents/skills/echo-review/SKILL.md .agents/skills/echo-address-review/SKILL.md`
   lists all three.
6. Docs: `grep -l "Simplified Technical English" CLAUDE.md README.md` lists both files.
7. Version bumped: `.claude-plugin/plugin.json` version is `0.7.0` (from `0.6.0`).
8. No em dashes ADDED by this change (pre-existing ones in touched files are out of scope).
   After `git add -A` so the new `skills/ste-writing/SKILL.md` is included, the added lines
   carry no em dash: `git diff --cached -U0 | grep '^+' | grep "—"` prints nothing (read the
   printed lines, not the `grep` exit code, which is 1 when the count is 0).
9. `python3 -m pytest tests/test_echo.py -q` and `bash tests/smoke.sh` stay green. Add a smoke
   assertion beside the template-skills loop (around smoke.sh lines 115-117): `test -f
   skills/ste-writing/SKILL.md` with `grep -q "^name:"` and `grep -q "^description:"`, and
   `test -e .agents/skills/ste-writing/SKILL.md` (test -e, since it is a symlink).
   `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0 (no code changed, sanity
   only).
