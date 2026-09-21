# Intent: Address code review comments as a first-class echo step

- **Ticket:** FEAT-6833
- **Stage:** Plan
- **Author:** Echo contributor
- **Status:** draft (awaiting `/echo:approve`)

## Problem
After echo ships a PR, review feedback arrives out of band: the review bot (`claude[bot]`)
and independent human reviewers leave inline comments and review threads. echo can see this
feedback (`/echo:watch` reads it and forwards new items to Jira, `bin/echo-watch:132-178`) but
it cannot act on it. A developer still has to read every thread, edit the code by hand, push,
and resolve each thread manually. This is exactly the "out-of-band" work that never appears in
intent/spec/plan, called out in this ticket's research doc
(`.echo/artifacts/FEAT-6833/research.md`, Part A8 and Part B14), and today it lives entirely
outside the loop.

## Proposed outcome
A single echo capability, `/echo:address-review`, that for the active ticket's open PR:
1. reads the open review threads and analyses the complete code plus the Jira ticket before
   changing anything,
2. posts a Jira comment stating the agreed changes,
3. drives the echo `builder` subagent to make the code changes,
4. pushes the changes to the existing PR branch (no new PR), and
5. resolves each inline review thread once the fix is pushed.
The developer runs one command and gets pushed, verified changes with the threads resolved and
the ticket updated, without leaving echo.

## Affected users / systems
- The single developer using echo on a repo with an open PR under review.
- GitHub PR review threads (read + resolve, via `gh` GraphQL).
- The Jira ticket (one agreed-changes comment, via the Atlassian MCP under Claude Code).
- echo internals: a new `commands/address-review.md`, a new `skills/address-review/SKILL.md`,
  a new `bin/echo-review-comments` CLI, a `followup` subcommand on `bin/echo-git`, helpers in
  `lib/echo_common.py`, the `builder`/`verifier` subagents (reused), and the Codex mirror.

## Constraints
- echo conventions: Python 3 standard library only, determinism in `bin/`/`lib/`, prose is
  model-driven, no em dashes in user-facing strings or docs, gates fail open, ticket regex
  `[A-Z]+-[0-9]+` and never fabricate a ticket, hooks/gates block only with exit code 2.
- Never store diffs, tokens, or secrets in artifacts (mirror `echo-watch`'s one-line
  truncation).
- Reuse what exists: the `builder` subagent for edits (it never commits or pushes), the Jira
  comment-ledger pattern (`echo-stage comment-needed`/`comment-done`), and `echo-verify` for
  proof.
- Non-goals: CI check failures (they stay with `/echo:watch`); rewriting `echo-watch`;
  auto-approving any echo gate.

## Open questions
1. Should the command also post a per-thread reply on GitHub, or only resolve the thread?
   Current leaning: resolve only (what the user asked for); an optional short reply can be
   best-effort and is not required for done.
2. Should a follow-up push rebase onto the base branch? Current leaning: no, to avoid needing a
   force-push on an already-pushed PR branch; keep `followup` a plain commit and push.

## How we know it worked (leading signals)
- Running `/echo:address-review` on a ticket with open review threads produces a pushed commit
  on the PR branch, a Jira comment with the agreed changes, and the addressed threads showing
  as resolved on the PR.
- Running it with no open PR or no unresolved threads exits cleanly and changes nothing
  (fail open).
- `python3 -m pytest tests/test_echo.py -q` and `bash tests/smoke.sh` stay green with new
  coverage for the added CLIs.
