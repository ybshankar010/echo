---
name: address-review
description: The methodology and safety rules for addressing open PR review threads as an echo step. Use when running /echo:address-review to analyse review feedback, fix it via the builder, verify, push a follow-up commit, and resolve the threads.
---

# address-review

Addressing review feedback is out-of-band work that never appears in intent/spec/plan:
the review bot and human reviewers leave inline threads after a PR ships. This skill turns
that into a repeatable echo step - analyse, agree, fix, verify, push, resolve - without
leaving the loop and without weakening the change.

## Method
- **Derive the ticket from the branch, never fabricate it.** The command operates on the
  currently checked-out PR branch. The ticket comes from that branch
  (`ec.ticket_from_branch()`); a passed `--ticket` that disagrees is a stop, not an override.
- **Confirm the gate is open first.** The plan-guard hook keys off the single echo active
  item. If the operated ticket is not the active item, the builder's edits are blocked
  mid-run. Confirm the match up front and stop with guidance rather than failing later.
- **Analyse before addressing.** Read the Jira ticket for intent and the complete code around
  each thread (not just the one-line body) before changing anything.
- **Agree in the ticket.** Post one Jira comment stating the changes you will make
  (prose only), best-effort and fail open. Never change the Jira status field.
- **Fix via the builder.** The `builder` subagent makes the edits and marks each thread
  `addressed`; it never commits or pushes. Fix the code, not the tests - never weaken, skip,
  or delete a test to go green.
- **Verify, then push.** Run `echo-verify` for proof. Only on a green verify push a follow-up
  commit with `echo-git followup` (no rebase, no new PR, ticket id and trailer enforced).
- **Resolve last.** Resolve a thread only after a green verify and a successful push, and only
  for threads you actually addressed. The per-thread ledger keeps re-runs idempotent.

## Safety rules
- Never store diffs, tokens, or secrets in artifacts, the ledger, or Jira comments; keep
  bodies one line only (mirrors `echo-watch`).
- Every command and PR interaction carries the ticket id and the Co-Authored-By trailer.
- Fail open: no `gh`/auth/remote/PR/threads means the command changes nothing and exits clean.
- Never self-approve an echo gate; leave approval to the developer.
- No em dashes; lean and concrete.

The command loads this skill the way `/echo:plan` loads `echo:plan-template`. Determinism
(thread enumeration/resolution, the ledger, the follow-up push) lives in the stdlib CLIs
`bin/echo-review-comments` and `bin/echo-git followup`; the orchestration lives in
`commands/address-review.md`.
