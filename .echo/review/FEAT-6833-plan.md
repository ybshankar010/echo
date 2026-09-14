# Plan review: FEAT-6833 — Plan/build checklist

- ts: 2026-09-14
- stage: plan (maker-checker complete)
- result: CLEAN after fixes (approved by owner)

## Critic findings and resolutions
- **Blocking 1 (Codex plan-template drift) - FALSE POSITIVE.** The critic said
  `.agents/skills/plan-template/SKILL.md` would go stale. Verified it is a SYMLINK to
  `skills/plan-template` (mode 120000, same inode 89565213), so editing the real file updates the
  Codex view automatically. No separate edit; plan notes this and Proof 3 asserts it via the symlink.
- **Blocking 2 (grep of two files passes on either) - FIXED.** Proof 3 now uses two separate
  `grep -q` checks `&&`-ed, one per file, so both plan-template and templates/plan.md must carry
  checkboxes.
- **Minor - Proof 4 aspirational:** now a concrete `grep -qi "fix-scope" commands/build.md` plus
  `grep -q "check-next"`.
- **Minor - Proof 10 scope regex unanchored:** allowed paths end-anchored so near-miss filenames
  do not false-match.
- **Minor - status.md wording:** left to prose per repo convention; not a gap.

## Confirmed sound (critic)
- The 3 pure fns are specified precisely (regex, section-scan boundary, marker-only rewrite,
  out-of-range no-op); match the parse_checks/slugify style.
- Smoke fixture path + `set-artifact --stage plan` interaction correct (defaults to the
  ticket-scoped plan path; does not require pre-existing file).
- Proof-section checkbox correctly excluded by the Order-of-work section scan.
- check-next fail-open vs check/uncheck exit-2 split coherent; build.md fix-scope exclusion maps to
  the real reviewer-driven rerun step.
- Baseline 62 tests pass.

## Note
No code has been written yet (this is the plan gate). Build will implement the 9-step Order of work.
