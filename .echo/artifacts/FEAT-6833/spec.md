# Spec: Address code review comments as a first-class echo step

- **Ticket:** FEAT-6833
- **Stage:** Design
- **Derived from:** intent.md (approved)
- **Status:** draft (awaiting `/echo:approve`)

## Overview
Add `/echo:address-review`: an echo command (with a paired skill) that, for the active
ticket's open PR, reads the open review threads, analyses the full code and the Jira ticket,
posts the agreed changes to Jira, has the `builder` subagent make the edits, verifies, pushes
a follow-up commit to the existing PR branch, and resolves each addressed thread. The
determinism (GitHub GraphQL for thread enumeration/resolution, a per-thread ledger, the
follow-up push) lives in stdlib `bin/` CLIs; the orchestration and prose live in the command
and skill. It reuses the existing `builder`/`verifier` subagents, the Jira comment-ledger
pattern, and `echo-verify`.

## Requirements
1. A new stdlib CLI `bin/echo-review-comments` exposes `fetch`, `mark`, and `resolve`, is
   executable, imports `echo_common as ec`, uses only the standard library, and always exits 0
   except on argparse errors (fail open).
2. `fetch [--ticket T]` resolves the active PR; with no `gh`/auth/remote/PR it prints nothing
   and exits 0. With a PR it lists review threads via `gh api graphql`, writes a human artifact
   at `.echo/review/<ticket>-comments.md`, and prints one tab-separated line per unresolved
   thread not already resolved in the ledger:
   `thread\t<node-id>\t<path>:<line>\t<author>\t<one-line body>`.
3. `mark --thread ID --status addressed [--commit SHA] [--ticket T]` records a thread as
   addressed in the ledger `.echo/review/<ticket>-threads.json`.
4. `resolve --thread ID [--ticket T] [--dry-run]` calls the GraphQL `resolveReviewThread`
   mutation; on success it stamps the ledger `status:"resolved"`. `--dry-run` prints the
   intended call and does not execute it. It fails open and reports per-thread success/failure.
5. `bin/echo-git` gains a `followup -m "<msg>" [--ticket T] [--staged] [--dry-run]` subcommand
   that: exits 2 if the current branch is base/`main`/`master`/empty; stages (`-A`, or `-u`
   with `--staged`); commits `"<ticket>: <msg>\n\n<TRAILER>"`; pushes the current branch; and,
   if `gh` is present, prints the existing PR url via `gh pr view --json url` and never runs
   `gh pr create`. Ticket resolution reuses the existing `resolve_ticket`.
6. `lib/echo_common.py` gains: `resolve_pr()` returning `{number,url,head_sha,owner,repo}` or
   `None`; a pure `parse_review_threads(graphql_json)` returning
   `[{id,is_resolved,is_outdated,path,line,author,body_oneline,url}]` with one-line truncated
   bodies and no secrets; thread-ledger helpers `thread_ledger_path`/`load_thread_ledger`/
   `save_thread_ledger` (fail open, non-dict coerced to `{}`); and `review_comments_relpath`.
7. `commands/address-review.md` orchestrates the eight-step playbook (fetch -> analyse code +
   Jira ticket -> Jira agreed-changes comment -> builder edits -> verify -> followup push ->
   resolve threads -> summarize) and never self-approves a gate.
7a. The command operates on the currently checked-out PR branch. It derives the ticket from the
    branch (`ec.ticket_from_branch()`); if `--ticket` is supplied and does not match the
    branch's ticket, it aborts with a clear message rather than acting on the wrong PR. It also
    confirms that ticket is the echo active item (so `echo-plan-guard` is open for the builder);
    if not, it aborts and tells the user to check out the PR branch (or set
    `plan_guard_override=true`), rather than letting the builder's edits be blocked mid-run.
8. `skills/address-review/SKILL.md` holds the reusable methodology; the command loads it the
   way `commands/plan.md` loads `echo:plan-template`.
9. A Codex mirror `.agents/skills/echo-address-review/SKILL.md` exists so `tests/smoke.sh`
   parity passes.
10. `tests/test_echo.py` and `tests/smoke.sh` cover the new CLIs and assets; the compile check
    passes for all `bin/echo-*`.

## Design
- **Thread enumeration (fetch).** `gh api graphql` query over
  `repository.pullRequest.reviewThreads` selecting
  `id,isResolved,isOutdated,path,line,comments{author.login,body,url}`. `resolve_pr()` supplies
  owner/repo/number via `gh pr view --json number,url,headRefOid` and `gh repo view --json
  owner,name`. `parse_review_threads` is a pure function over the decoded JSON so it is
  unit-testable without `gh`. The ledger at `.echo/review/<ticket>-threads.json` maps thread
  node id -> `{status, ts, commit}` so already-resolved threads are skipped and re-runs are
  idempotent. Both bot (`review_bot_login`) and human authors are addressed; the artifact
  labels bot threads for readability but does not filter them out.
- **Thread resolution (resolve).** GraphQL mutation
  `resolveReviewThread(input:{threadId:$id})`. Called once per addressed thread after the push,
  stamping the ledger. `--dry-run` supports a no-network test path.
- **Follow-up push.** A distinct `echo-git followup` path because `ship` always rebases and
  tries to open a new PR (`bin/echo-git:98-127`), which is wrong for adding commits to a PR
  already under review. `followup` reuses `resolve_ticket`, `TRAILER`, and `sh`; it does not
  create a branch or a PR and does not rebase (avoids a force-push on an already-pushed
  branch).
- **Orchestration.** The command reads the Jira ticket (`getAccessibleAtlassianResources` ->
  `getJiraIssue` under Claude Code; skipped under Codex per `CLAUDE.md`), spawns `builder` with
  the thread list as fix-scope (the same handoff style as `commands/build.md:38-46`; the
  builder never commits or pushes), runs `echo-verify` for proof, then `echo-git followup`,
  then `echo-review-comments resolve` per addressed thread.
- **Runtime gating.** `echo-plan-guard` (`bin/echo-plan-guard:62-70`) is keyed to the single
  echo active item, not to an arbitrary ticket. It is open only when the active item is at
  `ship`/`done` (>= `build`) with the plan gate approved. Since review feedback arrives out of
  band (the developer may have moved on to another ticket), the command must confirm the
  operated ticket IS the active item before invoking the builder; otherwise the builder's edits
  would be blocked (exit 2). On mismatch the command aborts with guidance (check out the PR
  branch, or set `plan_guard_override=true`) rather than failing mid-run.
- **PR/branch correctness.** `resolve_pr()` resolves the PR for the currently checked-out
  branch (`gh pr view`), not by ticket. The command therefore derives the ticket from the
  branch and treats `--ticket` as a guard (abort on mismatch), so it can never write artifacts
  or post Jira comments for one ticket while resolving a different branch's PR.

## Flagged concerns
- **Security:** Review comment bodies and Jira content can contain sensitive text. Mitigation:
  store only one-line truncated bodies in artifacts, never diffs/tokens/secrets (mirror
  `echo-watch._one_line`); the ledger stores ids and status only.
- **Security:** `resolve` and `followup` perform outward-facing GitHub actions. Mitigation:
  `--dry-run` for tests; resolution runs only after a green verify and a successful push; each
  action is per-thread and idempotent via the ledger.
- **Compliance:** All commits/PR interactions carry the ticket id and Co-Authored-By trailer;
  `followup` reuses `resolve_ticket` and never fabricates a ticket, per organization policy.

## Non-goals
- Fixing CI check failures (owned by `/echo:watch`).
- Refactoring `bin/echo-watch` to share `resolve_pr` (the helper is added for the new CLI; the
  watch path is left as-is).
- Auto-approving any echo gate, or opening a second PR.
- A vector/RAG memory system (that is the separate global-memory research, out of scope here).

## Acceptance criteria
- `python3 -m py_compile lib/echo_common.py bin/echo-*` exits 0.
- `python3 -m pytest tests/test_echo.py -q` passes, including: `parse_review_threads` filters
  resolved threads and truncates bodies; thread-ledger load/save/dedup; `echo-review-comments
  fetch` exits 0 with no PR; `echo-review-comments mark` stamps the ledger; `echo-review-comments
  resolve --dry-run` prints the intended call and does not touch the network; `echo-git
  followup` exits 2 with no ticket and exits 2 on the base branch; `echo-git followup --dry-run`
  prints the commit and push without running them.
- `bash tests/smoke.sh` passes with the new command, CLI, skill, and Codex mirror present.
- Manual: `python3 bin/echo-review-comments fetch --ticket FEAT-6833` in this repo (no PR)
  prints nothing and exits 0.
