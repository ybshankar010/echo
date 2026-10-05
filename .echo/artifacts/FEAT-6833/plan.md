Ticket: FEAT-6833
Stage: Build (kickoff)
Derived from: spec.md
Status: draft

# Write echo artifacts in Simplified Technical English

## Files that change
- `skills/ste-writing/SKILL.md` - NEW skill. Frontmatter `name: ste-writing` and a one-line
  `description`. Body states the full public ASD-STE100 writing rules, grouped by theme
  (sentences, words, verbs, procedures, warnings and cautions, punctuation and spelling),
  plus the scope boundary (prose only, never code, paths, commands, ticket ids). States the
  approved-word principles; does not reproduce the proprietary dictionary; points to the
  standard.
- `skills/intent-template/SKILL.md`, `skills/spec-template/SKILL.md`,
  `skills/plan-template/SKILL.md`, `skills/research-template/SKILL.md` - add one line in the
  Rules area: write the prose in Simplified Technical English; load `echo:ste-writing`. These
  four are symlinked from `.agents/skills/*-template`, so the edit reaches Codex with no extra
  step.
- `commands/ship.md`, `commands/address-review.md` - one line: write the `-m` descriptive
  prose in STE (load `echo:ste-writing`); keep the `TICKET: ` prefix, the `Ticket: <id>` line,
  and the Co-Authored-By trailer unchanged. `bin/echo-git` is not touched.
- `commands/review.md` - add STE to the reviewer prompt so the summary prose follows STE.
- `skills/address-review/SKILL.md` - add the STE pointer for the Jira comment and reply prose
  this skill writes (model-written prose, so STE applies).
- `.agents/skills/ste-writing` - NEW symlink to `../../skills/ste-writing` (a symlink, not a
  copy, matching the template mirrors).
- `.agents/skills/echo-ship/SKILL.md`, `.agents/skills/echo-review/SKILL.md`,
  `.agents/skills/echo-address-review/SKILL.md` - real copies, so each gets the same STE note
  as its `commands/*.md` source.
- `CLAUDE.md` - add one Conventions line naming the STE rule and the `ste-writing` skill.
- `README.md` - name the `ste-writing` skill.
- `.claude-plugin/plugin.json` - bump version `0.6.0` to `0.7.0`.
- `tests/smoke.sh` - add an assertion for the new skill beside the template-skills loop.

No change to `bin/`, `lib/`, hooks, the loop state machine, or the recap (deterministic).

## Order of work
- [x] 1. Write `skills/ste-writing/SKILL.md`: frontmatter + the full public ASD-STE100 rule
      set grouped by theme, the prose-only scope boundary, the approved-word principles, and a
      pointer to the standard (no proprietary dictionary).
- [x] 2. Add the STE reference line to the four template skills
      (`intent/spec/plan/research-template/SKILL.md`), inserted in each skill's Rules area
      beside the "No em dashes" rule. (Independent of step 1 text; can run in parallel.)
- [x] 3. Add the STE note to the commit/PR prose (`commands/ship.md`,
      `commands/address-review.md`), the review summary prose (`commands/review.md`), and the
      Jira comment/reply prose in `skills/address-review/SKILL.md`, keeping the ticket prefix
      and trailer wording intact (insert lines only; delete none).
- [x] 4. Codex parity: create the `.agents/skills/ste-writing` symlink to
      `../../skills/ste-writing`, and add the STE note to the real copies
      `echo-ship`, `echo-review`, `echo-address-review`.
- [x] 5. Docs: add the STE Conventions line to `CLAUDE.md`; name the skill in `README.md` and
      update its Codex-port sentence (~line 119, "the four template skills") to include
      `ste-writing`; check `.agents/skills/README.md` for a skill list to update too.
- [x] 6. Bump `.claude-plugin/plugin.json` version `0.6.0` to `0.7.0`.
- [x] 7. Tests: add the `skills/ste-writing` assertion to `tests/smoke.sh` beside the
      template-skills loop (lines 115-117): `test -f skills/ste-writing/SKILL.md` with
      `grep -q "^name:"` / `grep -q "^description:"`, and `test -e
      .agents/skills/ste-writing/SKILL.md` (test -e, since it is a symlink).
- [x] 8. Run Proof (below).

Steps 2 to 7 touch mostly disjoint files; step 1 writes the one source the others point to.

## Risks
- Drift across the sites that name STE. Mitigation: the substance lives only in
  `ste-writing`; every other site is a one-line pointer, so there is one source to maintain.
  A doc-sync test is a non-goal (same reasoning as past echo features).
- Copyright. Mitigation: the skill states the public writing rules and word principles only,
  with a pointer to the standard, and does not reproduce the approved-word dictionary.
- Em-dash convention. Pre-existing em dashes live in some touched files; this change must not
  ADD any. The symlinked templates are the same files on both sides, so no double counting.

## Proof
Run from repo root; all must pass.
1. New skill present and shaped: `test -f skills/ste-writing/SKILL.md`; it has `^name:` and
   `^description:`; its body names ASD-STE100 and the prose-only scope boundary.
2. Templates reference the skill:
   `grep -l "ste-writing" skills/intent-template/SKILL.md skills/spec-template/SKILL.md skills/plan-template/SKILL.md skills/research-template/SKILL.md`
   lists all four.
3. Commit/PR prose: `grep -l "ste-writing" commands/ship.md commands/address-review.md` lists
   both; `grep -l "ste-writing" skills/address-review/SKILL.md` lists it; those files still
   name the Co-Authored-By trailer and the ticket prefix. The edits only insert lines:
   `git diff --cached --numstat commands/ship.md commands/address-review.md` shows 0 deletions
   for each, so the trailer and prefix lines survive.
4. Review prose: `grep -in "ste-writing\|Simplified Technical English" commands/review.md`
   matches.
5. Codex parity: `test -e .agents/skills/ste-writing/SKILL.md` (new symlink resolves), and
   `grep -l "ste-writing" .agents/skills/echo-ship/SKILL.md .agents/skills/echo-review/SKILL.md .agents/skills/echo-address-review/SKILL.md`
   lists all three.
6. Docs: `grep -l "Simplified Technical English" CLAUDE.md README.md` lists both files.
7. Version: `.claude-plugin/plugin.json` version is `0.7.0`.
8. No em dash ADDED: after `git add -A`, `git diff --cached -U0 | grep '^+' | grep "—"` prints
   nothing (read the lines, not the grep exit code).
9. Green: `python3 -m pytest tests/test_echo.py -q` passes; `bash tests/smoke.sh` passes
   (with the new assertion); `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0.

## Definition of done
- The `ste-writing` skill holds the full public ASD-STE100 rule set; the four templates, the
  ship/address-review/review flows, and the Codex copies point to it; docs record the rule;
  the version is `0.7.0`.
- Proof steps 1 to 9 pass; no `bin/`/`lib/` change; no em dash added.
