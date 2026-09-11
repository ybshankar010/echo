# Review: FEAT-9999 plan (critic)

- ts: 2026-09-07
- target: `.echo/artifacts/FEAT-9999/plan.md` vs `.echo/artifacts/FEAT-9999/spec.md`
- verdict: SOLID (no blocking gaps)

## Blocking gaps
None. All 10 spec requirements map to a plan step or file; every named helper
(`_read_json`, `_write_json`, `now_iso`, `active_item`, `TICKET_RE`, `ensure_dirs`) was verified
to exist in `lib/echo_common.py`; `_write_json` already makes the parent dir; the argparse
subcommand pattern in `bin/echo-stage` matches; the Proof section follows the existing
`tests/test_echo.py` and `tests/smoke.sh` patterns and is runnable.

## Nits (all addressed in plan.md)
1. Data-leakage risk was in the spec but missing from the plan's Risks list. Added a Risks
   bullet: comments use only the per-stage templates, never diffs/secrets/tokens.
2. Requirement 6 (no comments during maker-checker iterations) had no explicit callout. Added
   a note in Order of work step 3 that the call site (flow step 5) sits outside the plan/build
   maker-checker loops, so no inner-iteration comments fire.
3. Gate-stop vs auto-advance template variant was not spelled out at the call site. Clarified
   in Order of work step 3: plain template on auto-advance, "awaiting your review" variant when
   `gate-mode` returned `stop`.
