# Plan review: FEAT-6833 (plan.md vs spec.md)

Verdict: no blocking gaps. Plan is buildable as written.

## Verified against code
- templates/REVIEW.md has `## Passes` (lines 3-6) with three bullets; `## "Important" means` and `## Cap nits` exist and stay unchanged.
- agents/reviewer.md: line 3 description names (bugs, security, compliance); "By default:" list at lines 14-19; em dash at line 27 confirmed.
- commands/review.md: pass string at line 10, em dash at line 13 confirmed.
- commands/build.md: pass string at line 34; important-only loop at line 38 confirmed (so YAGNI nits do not trigger the fix loop).
- Current em dash grep over the four files hits only the two lines the plan removes, so Proof 3 will go green.

## Coverage
Reqs 1-6 and acceptance criteria 1-5 all map to steps 1-5 and Proof 1-5 (Proof 6 is extra). Req 3 consequence is recorded in the reviewer.md bullet note. Nothing dropped.

## Findings (nits)
1. Proof 2: `grep -in "test"` is a weak check. It matches many incidental words, so it does not prove the guard names self-testing code. Prefer `grep -in "self-testing"` (spec acceptance 2 has the same looseness).
2. Proof 4: `git diff --name-only` runs on branch `main` with pre-existing dirty `.echo/` files and an untracked research file. Untracked files are not listed, and `.echo/` noise is expected. Run it after the branch is cut or filter with `-- bin lib tests` and expect empty output.
3. The plan itself contains em dashes (the "Files that change" bullets), against the repo no-em-dash convention for docs. Cosmetic, not covered by the acceptance grep.
4. Plan says REVIEW.md and reviewer.md use "identical wording", but the severity/override note appears only in reviewer.md. Intentional per the plan, but REVIEW.md will not state that YAGNI is a nit. Consider one clause there so a repo that copies the template gets the ranking too.
5. Step 2 replacement for line 27 ("look thorough. An empty") is fine, but it should keep the line wrap intact. Re-run Proof 3 after the edit.

Count of further nits: 0.
