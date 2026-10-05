Ticket: FEAT-6833
Stage: Design
Derived from: intent.md
Status: draft

# YAGNI review pass for echo's reviewer

## Overview
Add a fourth review pass, YAGNI, to echo's reviewer so it flags presumptive code
(capability, abstraction, config, or parameters added ahead of a current need) while
explicitly protecting the practices YAGNI depends on: refactoring, self-testing code,
and abstractions that reduce coupling for today's requirements. This is a prose change
to the review guidance and the sites that enumerate the passes; no determinism in
`bin/` or `lib/` changes.

## Requirements
1. `templates/REVIEW.md` gains a **YAGNI** bullet under `## Passes` phrased as a
    concrete rule: flag code with no current caller or requirement (an unused option or
    config flag, a parameter or generality no present requirement uses, a code path
    reachable only by a feature not yet in use, extensibility added "for later").
    (traces to intent: Proposed outcome; critic nit 4)
2. `templates/REVIEW.md` gains a short guard, `## YAGNI: do not flag`, stating what the
    pass must NOT flag: refactoring that eases change, self-testing code (tests, CI), and
    abstractions or simplifications that reduce or hold coupling for current
    requirements. (traces to intent: Constraints; Fowler "YAGNI requires malleable code")
3. YAGNI findings are quality findings, ranked below the existing "important" reservation
    (behavior-breaking, data-leaking, policy-breaching) and reported as nits under the
    existing five-nit cap. Consequence to state in the artifact: because
    `commands/build.md` only loops the builder on important findings, YAGNI findings will
    not trigger an auto-fix loop; they surface for the human to decide. This is intended.
    (traces to intent: Open questions, both leans; critic nit 2)
4. `agents/reviewer.md` carries the full YAGNI framing (the flag rule from req 1 and the
    do-not-flag guard from req 2) in its inline "By default:" list, mirroring how that
    list already restates bugs/security/compliance. The frontmatter `description` names
    YAGNI alongside bugs, security, compliance. (traces to intent: Affected systems;
    critic nit 3)
5. The reviewer prompts that enumerate passes name YAGNI: the string
    `(bugs, security, compliance)` becomes `(bugs, security, compliance, YAGNI)` at
    `commands/review.md:10` and `commands/build.md:34`. These carry the pass name only,
    not the substance. (traces to intent: Affected systems)
6. All four sites agree on the pass set after the change (REVIEW.md, reviewer.md list +
    description, review.md prompt, build.md prompt). (traces to intent: Constraints)

## Design
- Delivery reality (critic nit 3): the reviewer reads `REVIEW.md` from the TARGET repo
  root, but echo ships only `templates/REVIEW.md` and has no root `REVIEW.md`. So the
  agent's inline "By default:" list in `agents/reviewer.md` is the always-present
  fallback that actually makes the pass apply when echo reviews itself or any repo that
  copied the template earlier. Therefore the full YAGNI framing lives in BOTH
  `templates/REVIEW.md` and the `agents/reviewer.md` inline list. This mirrors the
  existing duplication: today both files already describe bugs/security/compliance in
  full. The two command prompts (`review.md`, `build.md`) reference the pass set by name
  only, exactly as they do now.
- Reuse the existing document structure and terse voice: the YAGNI pass is one bullet
  under `## Passes`; the guard is a short titled subsection so the flag rule cannot be
  read without its counter-list.
- Reuse the existing `## "Important" means` and `## Cap nits` sections unchanged;
  requirement 3 is met by wording (quality finding, nit) rather than a new severity or a
  second cap. The consequence that YAGNI findings never trigger `commands/build.md`'s
  builder fix loop (it loops only on important findings, build.md:38) is stated in the
  YAGNI bullet in `agents/reviewer.md` and here, so it is recorded, not discovered later.
- Combine/override behavior: `agents/reviewer.md` step 2 reads the target repo's
  REVIEW.md and applies the inline defaults. The YAGNI pass applies by default; a target
  REVIEW.md that lists passes without YAGNI opts out of it. Accepted limitation: a repo
  that copied the old template before this change keeps its own REVIEW.md and will not
  see YAGNI until it re-copies the template. echo itself has no root REVIEW.md, so the
  reviewer offers to copy the updated template or falls back to the inline list.
- No changes to `bin/`, `lib/`, hooks, or tests. The reviewer is model-driven; the
  guidance is the deliverable. Two pre-existing em dashes in files this change already
  touches (`agents/reviewer.md:27` and `commands/review.md:13`) are removed in passing to
  satisfy the repo's no-em-dash convention and keep the four-file em-dash acceptance check
  green.

## Flagged concerns
- Over-flagging risk: a blunt YAGNI pass could nag on every abstraction and make reviews
  noisy. Mitigation: the concrete flag rule (req 1) plus the explicit do-not-flag guard
  (req 2) plus nit-ranking under the five-nit cap (req 3). Not a security/compliance risk.
- Drift risk: four sites reference the pass set; the substance is duplicated in two
  (REVIEW.md and reviewer.md). Mitigation: keep the two command prompts name-only, and
  keep the two substantive copies short and identical in intent. A deterministic
  doc-sync test was considered (critic nit 1) and deferred as a non-goal below.

## Non-goals
- No YAGNI pass for the `critic` (artifact reviewer) or `address-review`.
- No enforced/deterministic YAGNI check, and no doc-sync unit test, in `bin/`/`lib/`/
  `tests/`. Rationale (critic nit 1): only four small files reference the pass set and
  the duplicated substance is two short blocks; a test harness for that is itself
  presumptive (YAGNI). If drift bites later, add the sync test then. Surfaced for the
  human at the plan gate.
- No new severity level and no separate YAGNI-specific cap.

## Acceptance criteria
1. `grep -n "YAGNI" templates/REVIEW.md agents/reviewer.md commands/review.md commands/build.md`
   shows the pass present in all four files.
2. Both substantive copies name the guard concepts, checked mechanically:
   `grep -in "refactor" templates/REVIEW.md agents/reviewer.md` and likewise for `test`
   and `coupling` each match in both files.
3. No em dashes anywhere in the four files after the change (the pre-existing dashes at
   `agents/reviewer.md:27` and `commands/review.md:13` are removed):
   `grep -n "—" templates/REVIEW.md agents/reviewer.md commands/review.md commands/build.md`
   returns nothing (exit 1).
4. No change under `bin/`, `lib/`, or `tests/`: `git diff --name-only` lists only docs
   and `.echo/` artifacts.
5. `python3 -m pytest tests/test_echo.py -q` and `bash tests/smoke.sh` stay green
   (nothing determinism-facing changed).
