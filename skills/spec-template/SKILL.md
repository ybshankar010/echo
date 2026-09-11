---
name: spec-template
description: The structure and rules for writing an echo spec.md (Design stage) from an approved intent.md. Use when running /echo:spec or generating the Design artifact. Applies policy while the spec is written and flags concerns.
---

# spec-template

A `spec.md` is the full requirements + design for the work item, produced from an
approved `intent.md`. Policy is applied while writing, not discovered in late review.

## Required sections
- **Header** — `Ticket:`, `Stage: Design`, `Derived from: intent.md`, `Status:`.
- **Overview** — one paragraph: what we are building and the shape of the solution.
- **Requirements** — numbered, testable statements. Each traces to the intent.
- **Design** — the approach: components, data/state, interfaces, key decisions.
- **Flagged concerns** — security, compliance, privacy, UX. Name the risk and the
  mitigation. If a concern needs a policy owner, say so.
- **Non-goals** — what this explicitly does not do.
- **Acceptance criteria** — the checks that will prove the build (feeds plan.md Proof).

## Rules
- Ground every requirement in the intent; label anything inferred as an assumption.
- Prefer reusing existing utilities/patterns over new ones; name them.
- Make acceptance criteria concrete enough to become tests.
- No em dashes; lean and concrete.

Write to `.echo/artifacts/<ticket>/spec.md` (artifacts are scoped per ticket; the
`Artifacts:` line from `echo-stage status` shows the folder), then
`echo-stage set-artifact --stage spec` (the path defaults to the ticket-scoped location).
Skeleton: `${CLAUDE_PLUGIN_ROOT}/templates/spec.md`.
