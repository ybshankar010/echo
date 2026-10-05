Ticket: FEAT-6833
Stage: Plan
Author: echo-contributor
Status: draft

# Write echo artifacts in Simplified Technical English

## Problem
echo writes its documents in free-form English. The intent, spec, plan, and research
artifacts, and the review and recap prose, use long sentences, passive voice, and varied
words for one idea. This makes the documents harder to scan and harder for a second reader,
or a model, to act on in one pass. The user wants every document that echo creates to follow
Simplified Technical English (ASD-STE100), a controlled language that keeps technical writing
short, active, and consistent.

## Proposed outcome
Every model-written echo text follows the ASD-STE100 writing rules where the rules apply:
active voice, short sentences, one instruction per sentence, one word for one meaning, and
approved sentence structure. This covers the artifacts (intent, spec, plan, research), the
review and recap prose, and the commit message and PR description prose. A single reusable
skill holds the full public STE rule set. The artifact templates and the commit/PR and
review flows point to that skill, so the guidance has one source of truth and new echo text
reads as Simplified Technical English.

## Affected users / systems
- The echo skill set: a new `ste-writing` skill, plus the `intent-template`,
  `spec-template`, `plan-template`, and `research-template` skills that generate artifacts.
- The prose that echo generates at review and recap time.
- The commit message and PR description prose (the `/echo:ship` and `/echo:address-review`
  flows and the `bin/echo-git` message text), with the required ticket prefix and the
  Co-Authored-By trailer kept intact.
- The repo docs that describe echo (CLAUDE.md conventions, README) so the rule is recorded.
- The plugin version in `.claude-plugin/plugin.json` (this is a new feature; bump it).

## Constraints
- Use the public ASD-STE100 writing rule set only. The official approved-word dictionary is
  proprietary, so the skill states the rules and the word principles, not the copyrighted
  word list.
- Apply STE to prose that echo writes, not to code, file paths, commands, ticket ids, or
  identifiers. STE never changes a command or a literal value. In commit messages and PR
  descriptions, STE shapes the descriptive prose only; the `TICKET: ` prefix, the
  `Ticket: <id>` body line, and the Co-Authored-By trailer stay exactly as the policy
  requires.
- Keep the existing no-em-dash convention; STE is added guidance, not a replacement.
- Do not weaken any gate, test, or determinism. The templates are prose; the rule is prose.
- Non-goal: no automated STE grammar checker in `bin/` or `lib/`, and no change to the loop
  state machine.

## Decisions (resolved at the intent gate)
- STE applies to commit messages and PR descriptions as well as the `.echo/` artifacts and
  the review/recap prose. The ticket prefix, the `Ticket: <id>` line, and the Co-Authored-By
  trailer stay as the policy requires; STE shapes only the descriptive text.
- No reviewer STE pass now. The templates instruct STE and the human gate catches drift. An
  enforced pass stays a separate future feature.
- The `ste-writing` skill encodes the full public ASD-STE100 writing rule set (all rule
  groups), not a subset, with a pointer to the standard. The approved-word dictionary stays
  out (proprietary); the skill states the word principles instead.

## Open questions
- None remaining.

## How we know it worked
- A new `ste-writing` skill exists and states the full public ASD-STE100 writing rule set in
  actionable form.
- The intent, spec, plan, and research templates reference the STE skill and tell the writer
  to apply it, and the ship and address-review flows apply STE to commit/PR prose.
- A newly generated artifact, and a new commit/PR description, read as Simplified Technical
  English: short active sentences, one instruction per sentence, consistent terms, with the
  required ticket prefix and trailer intact.
- The plugin version is bumped, and the unit tests and smoke test stay green.
