# Review instructions

## Passes
- **Bugs:** logic errors, broken edge cases, subtle regressions.
- **Security:** injection risks, auth gaps, secrets or PII in logs/errors.
- **Compliance:** change matches the active item's spec and plan under `.echo/artifacts/<ticket>/`.
- **YAGNI:** flag code with no current caller or requirement: an unused option or config flag, a parameter or generality no present requirement uses, a code path reachable only by a not-yet-used feature, or extensibility added "for later".

## YAGNI: do not flag
Refactoring that eases change, self-testing code (tests, CI), and abstractions or simplifications that reduce or hold coupling for current requirements. YAGNI targets speculative capability only, not code that makes today's code easier to change.

## "Important" means
Reserve for behavior-breaking, data-leaking, or policy-breaching findings.
Style and naming are nits.

## Cap nits
Report at most five nits per review; summarize the rest as a count.

## Do not report
Generated files (e.g. under `src/gen/`) and anything CI already enforces.
