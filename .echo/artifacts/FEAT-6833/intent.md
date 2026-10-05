Ticket: FEAT-6833
Stage: Plan
Author: Echo contributor
Status: draft

# Add a YAGNI pass to echo's code-review skill

## Problem
echo's reviewer runs three passes today (bugs, security, compliance). None of them
catches speculative, unused code: presumptive features, abstractions, config flags,
or parameters added for a future that has not arrived. Martin Fowler's YAGNI
("You Aren't Gonna Need It") names the real cost of this: cost of build, cost of
delay, cost of carry, and cost of repair. Right now nothing in the loop pushes back
on "we might need it later" code before it ships, so carry cost accrues silently.

## Proposed outcome
The reviewer gains a fourth pass, YAGNI, that flags presumptive capability added
ahead of a current need, while explicitly NOT flagging the things YAGNI protects:
refactoring, self-testing code, and abstractions that reduce coupling for today's
requirements. When a diff adds a code path with no current caller, an unused option,
or generality no present requirement uses, the reviewer names it and cites the file
and line, ranked as a quality finding (not "important").

## Affected users / systems
- echo's `reviewer` subagent (`agents/reviewer.md`) and the passes it applies.
- The canonical passes list in `templates/REVIEW.md`.
- The reviewer prompts that enumerate the passes: `commands/review.md`,
  `commands/build.md` (the build maker-checker checker step).
- Anyone running `/echo:review` or `/echo:build`, and by extension `/echo:flow`.

## Constraints
- Prose/instruction change only. No `bin/` or `lib/` determinism changes; no new
  Python. This is model-facing guidance, not enforced logic.
- Keep every pass description short and concrete, matching the existing terse style.
- No em dashes in user-facing strings or docs (repo convention).
- Keep the four pass enumerations in sync (REVIEW.md, reviewer.md inline list +
  description, review.md prompt, build.md prompt).
- Non-goal: adding YAGNI to the `critic` (artifact reviewer) or to `address-review`.

## Open questions
- Should YAGNI findings ever be "important"? Leaning no: they are quality/design
  findings, reported like nits, below behavior-breaking issues, per REVIEW.md's
  existing definition of "important".
- Do YAGNI findings count against the five-nit cap? Leaning yes, treated as nits, to
  avoid a second cap and keep reviews terse.

## How we know it worked
- REVIEW.md lists a YAGNI pass with a clear "do not flag" guard, and all four pass
  enumerations across the repo agree.
- A reviewer reading the passes would flag an unused abstraction/flag added "for
  later" and would NOT flag a coupling-reducing refactor of current code.
- Unit tests and smoke test stay green (no determinism touched).
