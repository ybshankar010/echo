Ticket: FEAT-6833
Stage: Build (kickoff)
Derived from: spec.md
Status: draft

# Add a YAGNI pass to echo's code-review skill

## Files that change
- `templates/REVIEW.md` — add a **YAGNI** bullet under `## Passes` (concrete flag rule)
  and a new `## YAGNI: do not flag` guard section. This is the template repos copy.
- `agents/reviewer.md` — add YAGNI to the frontmatter `description`; add a YAGNI bullet
  with the full flag rule + do-not-flag guard to the inline "By default:" list (this is
  the always-present fallback the reviewer reads when no root REVIEW.md exists).
- `commands/review.md` — add YAGNI to the pass enumeration in the reviewer prompt (name
  only), and remove the pre-existing em dash on line 13.
- `commands/build.md` — add YAGNI to the pass enumeration in the checker (reviewer)
  prompt (name only).

No files under `bin/`, `lib/`, `hooks/`, or `tests/` change.

## Order of work
- [x] 1. Edit `templates/REVIEW.md`: add the YAGNI bullet under `## Passes` and the
      `## YAGNI: do not flag` guard section. Exact wording below.
- [x] 2. Edit `agents/reviewer.md`: update line 3 `description` to name YAGNI; add the
      YAGNI bullet (flag rule + guard + "quality nit, not important" + the override note)
      to the inline "By default:" list in step 2; and remove the pre-existing em dash on
      line 27 ("look thorough — an empty" becomes "look thorough. An empty") to satisfy
      the no-em-dash convention.
- [x] 3. Edit `commands/review.md`: change `(bugs, security, compliance)` to
      `(bugs, security, compliance, YAGNI)` at line 10 (the reviewer prompt); and replace
      the em dash on line 13 ("auto-approval —" becomes "auto-approval;") to keep the
      four-file em-dash check green.
- [x] 4. Edit `commands/build.md`: change `(bugs, security, compliance)` to
      `(bugs, security, compliance, YAGNI)` at line 34 (the checker prompt).
- [x] 5. Run Proof (below): grep checks, em-dash check, name-only diff scope check, unit
      tests, smoke test.

Steps 1 to 4 touch disjoint files and could be done in any order; step 5 runs last.

### Exact wording (single source for steps 1 and 2)
Flag rule (one line):
> flag code with no current caller or requirement: an unused option or config flag, a
> parameter or generality no present requirement uses, a code path reachable only by a
> not-yet-used feature, or extensibility added "for later".

Do-not-flag guard:
> Refactoring that eases change, self-testing code (tests, CI), and abstractions or
> simplifications that reduce or hold coupling for current requirements. YAGNI targets
> speculative capability only, not code that makes today's code easier to change.

Severity + scope note (reviewer.md bullet only): "YAGNI findings are quality nits, not
important, so they do not trigger the build fix loop. This pass applies by default; a
target REVIEW.md that lists passes without YAGNI opts out of it."

## Risks
- Over-flagging (noisy reviews). Mitigation: the concrete flag rule bounds scope, the
  do-not-flag guard protects good design, and nit-ranking keeps YAGNI under the five-nit
  cap.
- Enumeration drift across the four sites. Mitigation: command prompts stay name-only;
  the two substantive copies (REVIEW.md, reviewer.md) use the identical wording above.
  A doc-sync test was considered and deferred (see spec Non-goals); acceptable because
  the surface is four small files.
- Delivery gap: editing only `templates/REVIEW.md` would not apply to echo itself (no
  root REVIEW.md). Mitigated by step 2 putting the full framing in the reviewer.md inline
  fallback.

## Proof
Run from repo root; all must pass.
1. Pass present in all four sites:
   `grep -l "YAGNI" templates/REVIEW.md agents/reviewer.md commands/review.md commands/build.md`
   expect all four paths listed.
2. Both substantive copies carry the guard concepts, checked mechanically:
   `grep -in "refactor" templates/REVIEW.md agents/reviewer.md`,
   `grep -in "test" templates/REVIEW.md agents/reviewer.md`, and
   `grep -in "coupling" templates/REVIEW.md agents/reviewer.md`
   each expect a match in both files.
3. No em dashes remain in any of the four files (the pre-existing one at reviewer.md:27
   is removed in step 2):
   `grep -n "—" templates/REVIEW.md agents/reviewer.md commands/review.md commands/build.md`
   expect no output (exit 1).
4. Scope is docs only:
   `git diff --name-only` lists only `templates/REVIEW.md`, `agents/reviewer.md`,
   `commands/review.md`, `commands/build.md` (plus `.echo/` artifacts); nothing under
   `bin/`, `lib/`, `tests/`.
5. Determinism intact:
   `python3 -m pytest tests/test_echo.py -q` passes, and `bash tests/smoke.sh` passes.
6. Compile check unaffected (sanity):
   `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0.

## Definition of done
- All four sites name the YAGNI pass; REVIEW.md and reviewer.md carry the full flag rule
  and do-not-flag guard.
- Proof steps 1 to 6 all pass.
- No `bin/`/`lib/`/`tests/` change; no em dashes added.
