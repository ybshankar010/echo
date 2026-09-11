# Review instructions

## Passes
- **Bugs:** logic errors, broken edge cases, subtle regressions.
- **Security:** injection risks, auth gaps, secrets or PII in logs/errors.
- **Compliance:** change matches the active item's spec and plan under `.echo/artifacts/<ticket>/`.

## "Important" means
Reserve for behavior-breaking, data-leaking, or policy-breaching findings.
Style and naming are nits.

## Cap nits
Report at most five nits per review; summarize the rest as a count.

## Do not report
Generated files (e.g. under `src/gen/`) and anything CI already enforces.
