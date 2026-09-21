# Plan: Address code review comments as a first-class echo step

- **Ticket:** FEAT-6833
- **Stage:** Build (kickoff)
- **Derived from:** spec.md (approved)
- **Status:** draft (awaiting `/echo:approve`)

## Files that change
- `lib/echo_common.py` — add `resolve_pr()`, pure `parse_review_threads()`, thread-ledger
  helpers (`thread_ledger_path`/`load_thread_ledger`/`save_thread_ledger`), and
  `review_comments_relpath()`. Reuse `review_dir()` (line 227) and mirror the Jira-ledger
  helpers (lines 316-328).
- `bin/echo-review-comments` — new stdlib CLI with `fetch`/`mark`/`resolve` subcommands.
- `bin/echo-git` — add a `followup` subcommand next to `ship`; reuse `resolve_ticket`,
  `TRAILER`, and `sh` (not `slugify`: `followup` never creates a branch).
- `commands/address-review.md` — new command, thin playbook that loads the skill.
- `skills/address-review/SKILL.md` — new skill (methodology + safety rules).
- `.agents/skills/echo-address-review/SKILL.md` — Codex mirror for smoke parity.
- `tests/test_echo.py` — unit + subprocess tests for the new helpers and CLIs.
- `tests/smoke.sh` — asset-presence checks (and command-loop entry if it enumerates commands).
- `CLAUDE.md` — mention `/echo:address-review` in the "Building enhancements (the echo way)"
  prose where the other slash commands are described (the "## Commands" section is build/test
  invocations only, not a slash-command list). Carries to `AGENTS.md` via the symlink.

## Order of work
- [x] 1. Add the `lib/echo_common.py` helpers (`resolve_pr`, `parse_review_threads`, thread
      ledger, `review_comments_relpath`). Pure functions first so tests can target them.
- [x] 2. Write `bin/echo-review-comments` (`fetch`/`mark`/`resolve`), `chmod +x`. Fail open,
      one-line bodies only, ledger-backed dedup.
- [x] 3. Add `echo-git followup` (abort on base branch, commit + push, print existing PR url,
      never `gh pr create`, no rebase).  <!-- parallel with step 2: disjoint files -->
- [x] 4. Write `commands/address-review.md` (the eight-step playbook, with step 1 deriving the
      ticket from the current branch, aborting on a `--ticket` mismatch, and confirming the
      ticket is the echo active item so plan-guard is open before the builder runs) and
      `skills/address-review/SKILL.md`, plus the `.agents/skills/echo-address-review/SKILL.md`
      Codex mirror.  <!-- parallel with steps 2-3: disjoint files -->
- [x] 5. Add tests to `tests/test_echo.py` (pure helpers; `fetch` no-PR fail-open; `mark`
      ledger stamp; `resolve --dry-run` no-network; `followup` ticket/base-branch/dry-run) and
      add `address-review` to the hardcoded command loop in `tests/smoke.sh` (lines ~89-93) with
      the Codex-mirror `name:`/`description:` frontmatter so the new mirror is actually asserted.
- [x] 6. Mention `/echo:address-review` in the `CLAUDE.md` "Building enhancements" prose; run
      the compile check, pytest, and smoke test; fix the code until all green.

## Risks
- **Wrong-PR resolution:** `resolve_pr()` resolves by the checked-out branch, not by ticket, so
  running the command with a mismatched `--ticket` or a stale branch could act on the wrong PR.
  Mitigate: the command derives the ticket from the branch and aborts on a `--ticket` mismatch
  (step 4), never writing artifacts/Jira for a ticket whose PR was not resolved.
- **Plan-guard blocks the builder:** plan-guard keys off the single active item; if a different
  ticket became active, the builder's edits are blocked (exit 2). Mitigate: the command confirms
  the operated ticket is the active item before invoking the builder and aborts with guidance
  (check out the PR branch, or set `plan_guard_override=true`) rather than failing mid-run.
- GraphQL query shape wrong or `gh` version differences — mitigate by keeping `parse_review_threads`
  pure and unit-tested against a captured JSON fixture, and by failing open when `gh` errors.
- `followup` push rejected if the branch diverged from remote — mitigate by not rebasing and by
  surfacing the push failure (exit non-zero from git, reported), never force-pushing silently.
- Overwriting the prior FEAT-6833 artifacts — accepted: the standing bucket ticket reuses
  ticket-scoped artifacts and the prior content is preserved in git history.
- Codex-mirror drift breaking `tests/smoke.sh` — mitigate by adding the mirror in the same step
  as the command and running smoke before done.

## Proof (verifies the build; run at the Test stage)
- `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0.
- `python3 -m pytest tests/test_echo.py -q` passes, including new tests:
  `parse_review_threads` drops resolved threads and truncates bodies; thread-ledger
  load/save/dedup; `echo-review-comments fetch` exits 0 with no PR (fail open);
  `echo-review-comments mark` stamps the ledger; `echo-review-comments resolve --dry-run` prints
  the intended call and touches no network; `echo-git followup` exits 2 with no ticket;
  `echo-git followup` exits 2 on the base branch; `echo-git followup --dry-run` prints the
  commit and push without executing them.
- `bash tests/smoke.sh` passes (new command/CLI/skill/Codex-mirror assets present).
- Manual sanity: `python3 bin/echo-review-comments fetch --ticket FEAT-6833` in this repo (no
  PR) prints nothing and exits 0.

## Definition of done
All Proof checks are green, the six Order-of-work steps are complete, the new command/skill/CLI
follow echo conventions (stdlib only, executable bit, fail open, exit-2 gating, no em dashes,
ticket never fabricated), and the change is ready to ship as one ticketed PR.
