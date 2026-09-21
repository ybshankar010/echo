Question: What is needed to implement "global memory" for the echo agent, so decisions on a new
ticket can be informed by prior tickets, and so issues that never originate in intent/spec/plan
(code-review comments, CI failures, testing-surfaced bugs) still become durable, recallable
knowledge? How does the industry handle both problems?
Date: 2026-09-17
Ticket or Topic: FEAT-6833 (standing research bucket ticket; this research is not itself a build)
Status: draft

## Scope

In scope:
- What echo persists today on disk, and which of it is per-ticket vs cross-ticket/global.
- Whether any current echo mechanism lets a new ticket's intent/spec/plan draw on a prior
  ticket's decisions, patterns, or mistakes.
- Whether "out-of-band" signals (review comments, CI failures, test-surfaced bugs) that do not
  originate in intent/spec/plan are captured anywhere durable today, and if so, how far that
  capture reaches (ephemeral vs durable, ticket-scoped vs global).
- The parent Claude Code harness's own file-based memory (MEMORY.md + per-fact files) as a
  concrete, already-in-use reference design.
- Named industry systems and general techniques for agent long-term memory, with emphasis on
  how "out-of-band" learnings (not from a spec) get written back into durable memory.
- Concrete design options for echo's own global memory, given its stdlib-only/deterministic
  constraints, and the open questions the intent stage would need to resolve.

Out of scope: implementing anything. No code edits were made. This document does not decide
the design; Part C is explicitly inference to hand to the intent/spec stage.

## Findings

### Part A — echo's current memory, grounded in the codebase

**A1. State is a single JSON file with one "active" item; all other items are just inert history.**
`lib/echo_common.py` defines `default_state()` as `{"version": 1, "active": None, "items": {}}`
(echo/lib/echo_common.py:284-285) and `active_item()` returns only the item named by
`state["active"]` (echo/lib/echo_common.py:343-348). The live `.echo/state.json` in this repo has
three items (`FEAT-3816`, `FEAT-9999`, `FEAT-6833`) but `"active": "FEAT-6833"` — the other two
tickets' records sit in the JSON untouched and are never read by any code path except direct
lookup by ticket id.
Source: <repo-root>/lib/echo_common.py:284-348;
<repo-root>/.echo/state.json (read directly).

**A2. Every SDLC artifact is scoped per ticket, by construction.**
`artifact_relpath(ticket, stage)` returns `.echo/artifacts/<ticket>/<stage>.md`
(echo/lib/echo_common.py:108-110), and the comment on that function reads "scoped per ticket so
items never collide." There is no repo-global artifact path anywhere in `echo_common.py`.
Source: <repo-root>/lib/echo_common.py:108-110.

**A3. `commands/intent.md` only ever reads research for the *same* ticket, never prior tickets.**
Step 3 of the intent command says: "If prior research exists for this ticket at
`.echo/artifacts/<ticket>/research.md` (or I point you at a `.echo/research/<slug>.md`), read it
first and ground the intent in its findings... Fail open: if there is no research doc, just
proceed." There is no instruction anywhere in this file, or in `plan.md`, `spec.md`, `build.md`,
to look at any other ticket's intent/spec/plan/review/verify artifacts.
Source: <repo-root>/commands/intent.md:18-20.

**A4. A repo-wide grep for cross-ticket language in commands/agents returns nothing.**
`grep -rn "episodes\|recap\|previous ticket\|prior ticket\|cross-ticket\|other ticket"
commands/ agents/` produced no matches. The `critic` subagent (agents/critic.md:13-17) explicitly
scopes itself to "the caller passes you the concrete paths" for one ticket's artifacts. There is
no code or prompt anywhere in the repo that a new ticket's intent, spec, or plan stage reads a
different ticket's artifacts, `episodes.jsonl`, or `recap.md`.
Source: command run `grep -rn "episodes\|recap\|previous ticket\|prior ticket\|cross-ticket\|other
ticket" commands/ agents/` in <repo-root> (no output);
<repo-root>/agents/critic.md:13-17.

**A5. `recap.md` is a single overwritten file, always about the *currently active* item only.**
`bin/echo-capture` (Stop/SessionEnd hook) writes `.echo/recap.md` by opening it in `"w"` mode
(truncate-and-overwrite) each time, populated only from `ec.active_item(state)`:
ticket, title, stage, gate, branch, last commit, changed files (echo/bin/echo-capture:37-82,
`with open(ec.recap_path(), "w", ...)` at line 67). There is exactly one recap file
(`ec.recap_path()` returns a single fixed path, echo/lib/echo_common.py:239-240) for the whole
repo, so if a different ticket becomes active, its recap overwrites the previous ticket's. This
matches the current file on disk: `.echo/recap.md` currently shows only `FEAT-6833`, even though
`.echo/state.json` has two other items.
Source: <repo-root>/bin/echo-capture:37-82;
<repo-root>/lib/echo_common.py:239-240;
<repo-root>/.echo/recap.md (read directly).

**A6. `episodes.jsonl` is append-only and does hold cross-ticket history, but nothing reads it back.**
The same `echo-capture` hook appends one JSON line per Stop/SessionEnd event to
`.echo/episodes.jsonl` (echo/bin/echo-capture:55-64): `{ts, ticket, stage, branch, last_commit,
changed}`. This file is append-only (`open(..., "a", ...)`) and the live file has 101 lines, so it
*does* technically retain a chronological, cross-ticket record (an episodic log in the "episodic
memory" sense industry frameworks use, see Part B). But no `bin/echo-*` script, command, or agent
prompt anywhere in the repo reads `episodes.jsonl` back in — `echo-recall` (the SessionStart hook)
only reads `recap.md` (single latest snapshot) and the active item from `state.json`
(echo/bin/echo-recall:25-68), never `episodes.jsonl`. So the raw facts for a full episodic history
exist on disk, but there is no retrieval path from them into any prompt.
Source: <repo-root>/bin/echo-capture:55-64;
<repo-root>/lib/echo_common.py:243-244;
<repo-root>/bin/echo-recall:25-68; `wc -l .echo/episodes.jsonl`
= 101 (command run in repo).

**A7. `echo-recall` (SessionStart/PostCompact) is the only automatic context injection, and it is
narrow by design.** It prints the active item, its stage/gate, the latest artifact path, and up to
1500 characters of `recap.md` (`RECAP_MAX = 1500`, echo/bin/echo-recall:14, 58-66). It is silent
(exit 0, no output) if echo is not initialized. This is echo's entire "memory recall" surface
today; it recalls state about the one active ticket, not lessons from other tickets.
Source: <repo-root>/bin/echo-recall:1-73.

**A8. Out-of-band signals (CI failures, review comments) are captured, but only into a per-ticket,
overwritten artifact plus one-shot Jira comments — never into durable, reusable memory.**
`bin/echo-watch run` (echo/bin/echo-watch:274-327) polls `gh pr checks` and `gh` review/PR
comments for the *active* ticket's PR, then calls `write_artifact()` which opens
`.echo/verify/<ticket>-ci.md` in `"w"` mode each time (echo/bin/echo-watch:217-222) — i.e. each run
overwrites the previous result for that ticket; there is no history of past CI failures or past
review comments retained anywhere, even per ticket. `commands/watch.md` step 3 says any new
CI-failure or review-comment event gets posted once as a Jira comment ("echo: " + summary),
deduplicated via a per-ticket ledger (`echo-stage comment-done`,
<repo-root>/commands/watch.md:22-31) — but that Jira comment is
a one-time notification, not a queryable memory the agent reads back on a future ticket. Similarly
`bin/echo-verify` writes `.echo/verify/<task>.md` (echo/bin/echo-verify: writes to
`os.path.join(ec.verify_dir(), f"{task}.md")`) which is also overwritten on each verify run
(opens in default write mode), so a test failure from three verify-runs ago is gone. Code-review
findings from `agents/reviewer.md` (invoked by `commands/review.md`) are reported to the human in
chat and are not written to any artifact at all in the reviewed commands.
Source: <repo-root>/bin/echo-watch:217-222,274-327;
<repo-root>/commands/watch.md:1-35;
<repo-root>/bin/echo-verify (read in full, `os.path.join`
write path and default `open` mode);
<repo-root>/commands/review.md:1-15.

**A9. Concrete gap statement.** Echo has: (a) durable per-ticket artifacts (intent/spec/plan,
never cross-referenced across tickets); (b) one global-but-single-item recap (`recap.md`,
overwritten, only ever about the active ticket); (c) one global append-only fact log
(`episodes.jsonl`) that is written but never read back by any component; (d) per-ticket,
overwritten watch/verify artifacts that capture out-of-band signals (CI, review comments) only
transiently and forward them to Jira as one-shot notifications. Echo has **no** mechanism today
by which a new ticket's intent, spec, or plan stage learns from a previous ticket's decisions,
mistakes, or review feedback. This is inference drawn directly from A1-A8 (no single line states
"there is no cross-ticket memory" — this is the logical conclusion of what does and does not
exist), not a fabricated claim.
Source: inference from A1-A8 above.

**A10. Config defaults show where equivalent switches for other gates live, useful as a precedent
for how a memory feature could be toggled.** `DEFAULT_CONFIG` in echo_common.py holds flags such as
`verify_gate`, `watch_gate`, `plan_guard`, `maker_checker` (echo/lib/echo_common.py:28-42), and
`load_config()` merges a partial on-disk `config.json` over these defaults
(echo/lib/echo_common.py:297-303) — confirmed live: the repo's own `.echo/config.json` only has 6
of the ~13 default keys, and `load_config()` fills in the rest. Any new memory feature would
plausibly follow the same pattern (a `config.json` flag, defaulted, merged).
Source: <repo-root>/lib/echo_common.py:28-42,297-303;
<repo-root>/.echo/config.json (read directly, 6 keys present).

**A11. The parent Claude Code harness already runs a working "global memory" pattern next to
echo, observed directly in this session.** The harness maintains
`~/.claude/projects/<encoded-project-path>/memory/MEMORY.md`, a short index of one-line bulleted
pointers, each linking to a separate per-fact markdown file in the same directory
(`FEAT-6833-research-bucket.md` in this case). The index's content was injected verbatim into this
session's system context at session start (visible as the literal text "Contents of
.../memory/MEMORY.md (user's auto-memory, persists across conversations)" in this session's own
system reminders) — i.e. the index is proactively loaded every session. The per-fact file was
*not* pre-loaded; it had to be fetched explicitly with the Read tool, and doing so returned an
extra system-reminder: "This memory is 5 days old. Memories are point-in-time observations, not
live state — claims about code behavior or file:line citations may be outdated. Verify against
current code before asserting as fact." The per-fact file itself is a normal markdown file with
YAML frontmatter (`name`, `description`, `metadata: {node_type: memory, type: project,
originSessionId, modified}`) followed by prose, structured as a short "Why" and "How to apply"
write-up.
Source: this session's own system reminder (literal MEMORY.md contents, quoted above); direct Read
of <local-claude-memory-root>/memory/MEMORY.md
and .../memory/FEAT-6833-research-bucket.md (both read directly in this session, including the
injected staleness system-reminder on the second).

**A12. Third-party (unofficial) corroboration of the mechanics of A11.** A community writeup
describes the same architecture: an index file capped at "200 lines" injected into the system
prompt each session, with a documented behavior that when MEMORY.md is empty Claude sees a prompt
to "save it here" when it notices a cross-session pattern, and that automatic reading of separate
topic files (beyond the index) is gated behind an internal, disabled-by-default feature flag. This
source is a third-party blog, not an Anthropic doc, so it is corroborating but not primary; I
labeled it as such and it is consistent with what I observed directly in A11 (the per-fact file
was not auto-loaded, matching "reading isn't automatic").
Source: https://giuseppegurgone.com/claude-memory (fetched).

### Part B — industry practice

**B1. Claude Code's own CLAUDE.md + `@import` layer (static, not learned) — for comparison against
its separate auto-memory (A11/A12).** This project's own `CLAUDE.md` files (org, user, and repo
level, all shown verbatim in this session's system context) are hand-written, hierarchical,
always-loaded instruction files — the "static instruction layer" pattern also used by other tools
(see B4). This is distinct from the auto-memory directory in A11, which is written by the model
itself as it works.
Source: this session's own system context (the three CLAUDE.md files reproduced verbatim at the
top of the conversation).

**B2. Anthropic's API-level "memory tool" (client-side, developer-implemented) — a different,
more general mechanism than Claude Code's own auto-memory.** Anthropic's public docs describe a
`memory_20250818` tool: Claude requests `view`/`create`/`str_replace`/`insert`/`delete`/`rename`
operations against a `/memories` path prefix, and the *calling application* (not Anthropic)
executes each operation against storage it owns (filesystem, DB, cloud). The docs state: "Claude
automatically checks its memory directory before starting a task. As it works, Claude stores what
it learns in files under `/memories` and reads them back in later conversations." The docs
explicitly recommend this for software projects spanning multiple agent sessions: an
"initializer session" sets up a progress log, feature checklist, and startup-script reference;
each subsequent session reads those files first; each session updates the progress log before
ending. This is explicitly a "just-in-time" retrieval design (full small-file reads on demand)
rather than embedding/vector search, and it is meant to survive context-window resets/compaction.
Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool (fetched).

**B3. Cursor "Memories."** Distinct from Cursor Rules (which are deliberately authored and
versioned in the repo). Memories are short (sentence-length) facts a background model proposes
while the user works ("this repo uses pnpm, not npm"), which the user approves before they are
saved; the agent can also be told directly to "remember" something. Memories are scoped to the
current project/repo and are personal to the user's Cursor setup — "they don't live in your repo,
they aren't versioned, and your teammates never see them." They are pulled into future
conversations automatically once approved; there is a background-generation toggle in Cursor
Settings -> Rules -> "Generate Memories."
Source: web search of Cursor's documentation and community sources (docs.cursor.com/context/memories
redirected to cursor.com/docs during fetch; content below is drawn from the WebSearch result
snippets of docs.cursor.com and localskills.sh, not a directly fetched primary page — flagged as
weaker sourcing than B2).

**B4. GitHub Copilot custom instructions (static) + "Agentic Memory" (emerging, not
user-configurable).** The primary mechanism is `.github/copilot-instructions.md` (repo root),
auto-included in every chat/agent interaction in that workspace, plus path-scoped
`.github/instructions/*.instructions.md` files with YAML frontmatter selecting which files/dirs
they apply to. This is a static, hand-authored layer, the same family as CLAUDE.md/AGENTS.md.
Separately, GitHub's own docs note an "Agentic Memory" capability that is "not customizable from
the user's perspective" and is expected to "likely be enabled by default" over time to improve
codebase/standards understanding — i.e. Copilot's automatic, learned memory is a black box from
the user's side today, unlike Cursor's or Codex's user-visible memory files.
Source: https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot
and https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide/add-repository-instructions-in-your-ide
(via WebSearch result snippets; not directly WebFetched in this session).

**B5. OpenAI Codex: AGENTS.md (static) vs. Memories (generated, separate).** Codex's own
documentation draws exactly the same split echo would need to draw: "AGENTS.md is the static
instruction layer... Codex reads at the start of every session," while "Memories is the generated
layer where Codex itself summarizes prior sessions in the background and writes the summaries to
`~/.codex/memories/`, which the agent then reads on subsequent sessions." The write pipeline is
described as two-phase: "Phase 1 handles per-rollout work by claiming a startup job, sampling the
conversation against a strict-schema extraction prompt, and redacting secrets before anything hits
disk; Phase 2 handles the merge by acquiring a global lock, preparing a workspace, running a
consolidation sub-agent, and writing the diff." AGENTS.md load order walks from a global
`~/.codex/AGENTS.md`/`AGENTS.override.md` down through the project root to the current working
directory.
Source: WebSearch result summary of https://developers.openai.com/codex/memories and
https://github.com/openai/codex/blob/main/docs/agents_md.md (the memories.md page itself
redirected to learn.chatgpt.com during a direct WebFetch attempt and was not re-fetched; content
here is from the WebSearch summary, flagged as secondary sourcing for the exact wording).

**B6. Aider: repo map (structural, not learned) + conventions file (static, hand-written).**
Aider's repo map is a graph-ranked summary of the whole repository (classes/functions/signatures)
computed fresh each run via tree-sitter/ctags, not a memory of past sessions. Its "conventions"
file (e.g. `CONVENTIONS.md`) is a plain markdown file the user writes by hand, loaded with
`/read CONVENTIONS.md`, on the CLI with `--read`, or permanently via `.aider.conf.yml`'s `read:`
key; loading it this way marks it read-only and cacheable. Aider does not learn or update
conventions automatically — it is entirely static, closest to CLAUDE.md/AGENTS.md/
copilot-instructions.md in the taxonomy, not to Cursor Memories or Codex Memories.
Source: https://aider.chat/docs/repomap.html (via WebSearch) and
https://aider.chat/docs/usage/conventions.html (fetched).

**B7. Windsurf Cascade "Memories."** Auto-generated during conversation when Cascade "believes"
something is worth remembering, or created explicitly on request ("create a memory of..."). Stored
locally per workspace at `~/.codeium/windsurf/memories/`, scoped to that workspace so memories
never cross projects. Memories are deliberately short (a sentence or two) and are retrieved by
Cascade "when it believes they're relevant" — i.e., relevance-triggered recall rather than a fixed
index always injected. Example given: correcting Cascade's output once ("always use named exports")
becomes a standing memory referenced automatically in later sessions.
Source: WebSearch summary of https://docs.windsurf.com/windsurf/cascade/memories (not directly
WebFetched; flagged as secondary sourcing).

**B8. Devin "Knowledge."** An explicit, curated knowledge base: each item has content plus a
required "Trigger Description" that Devin uses to decide when to recall that item — described
directly as "Devin will retrieve a Knowledge item when its current work is related to the
specified triggers." Items can be scoped to no specific repo (contextual), one repo, or all repos.
Crucially for the "out-of-band" question: "Devin will automatically suggest Knowledge to remember
based on your feedback in chat," and the user can edit/regenerate/dismiss the suggestion before it
is saved — i.e. a human-in-the-loop write path from live correction/feedback into durable, reusable
knowledge, trigger-indexed rather than always-loaded.
Source: https://docs.devin.ai/product-guides/knowledge (fetched).

**B9. General technique landscape — memory taxonomy.** LangChain's LangMem SDK and its docs use
the same three-way split found across the cognitive-architecture literature: *semantic* memory
(facts/preferences), *episodic* memory (specific past experiences, "how I solved this before,"
stored and reused as few-shot examples), and *procedural* memory (how-to knowledge, realized in
LangMem as updates to the agent's own system prompt via a "prompt optimizer" using
reflection-based (`metaprompt`), critique-then-propose (`gradient`), or unified (`prompt_memory`)
methods). LangMem's stated recall strategies split into "data-independent recall" (procedural
memory kept permanently in the prompt), "data-dependent recall" (semantic memories triggered by
embedding similarity), and "contextual recall" (similarity + context + recency combined); memories
are namespaced (e.g. by user id) to avoid cross-contamination.
Source: https://www.langchain.com/blog/langmem-sdk-launch (fetched).

**B10. MemGPT / Letta — hierarchical memory with a self-editing core.** MemGPT's "LLM OS" splits
memory into in-context "core memory" (the agent's persona and known facts about the user/task,
directly editable by the agent itself via `core_memory_append`/`core_memory_replace` tools) and
out-of-context "archival memory" (external, vector-database-backed storage, e.g. Chroma/pgvector,
searched via `archival_memory_search`). All memory access in Letta is tool-mediated, so the
storage backend for archival memory is swappable.
Source: WebSearch summary of https://docs.letta.com/letta-memgpt (not directly WebFetched;
flagged as secondary sourcing).

**B11. Mem0 — extraction/update pipeline for conversational memory.** Mem0's pipeline has an
"extraction" phase (an LLM reads a new user/assistant message pair and pulls out candidate facts)
and an "update" phase where a tool-call step decides ADD / UPDATE / DELETE / NOOP for each
candidate against existing memory, explicitly to avoid duplicate or stale facts; a newer
single-pass "ADD-only" mode does one LLM call per turn and accumulates rather than overwriting.
Retrieval blends semantic (embedding) search, BM25 keyword matching, entity-link boosting, and
recency weighting.
Source: https://github.com/mem0ai/mem0 (fetched).

**B12. Generative Agents ("memory stream" + reflection) — the foundational cognitive-architecture
reference most of the above cite.** Park et al. (2023) give each agent a single chronologically
ordered "memory stream" of every observation, reflection, and plan. Retrieval scores each memory
by a weighted combination of recency (exponential decay), relevance (embedding similarity to the
current situation), and importance (a self-assessed integer score assigned when the memory was
written). Periodically the agent "reflects": it clusters recent related observations and
synthesizes a higher-level statement (their example: "Klaus has been eating alone and seems
withdrawn"), which is itself written back into the memory stream and can be retrieved alongside
raw observations later. This importance-weighted write, and recency+relevance+importance-weighted
read, is the design many of the "index + per-fact-file" and "reflection" patterns above trace back
to.
Source: WebSearch summary quoting the paper's mechanism (direct fetch of the ACM full-text page at
https://dl.acm.org/doi/fullHtml/10.1145/3586183.3606763 returned HTTP 403 and was not accessible;
content here is from the WebSearch snippet, not a directly fetched primary page — flagged as
secondary sourcing pending a successful primary fetch).

**B13. Reflexion — verbal self-critique as the write trigger for a bounded memory buffer.**
Reflexion pairs an Actor, an Evaluator, and a Self-Reflection model. After each trial the Evaluator
scores the trajectory (success/fail or a scalar reward); the Self-Reflection model turns that
sparse signal into a specific verbal summary, which is appended to a long-term memory buffer
explicitly bounded to "1-3 experiences" to fit context limits. On the next attempt, the Actor
conditions its next decision on both the current observation and the stored reflections. This is
the clearest primary-source mechanism for "how does a failure become a durable, reusable lesson
without retraining the model" — directly relevant to echo's CI-failure and test-failure case.
Source: https://arxiv.org/html/2303.11366 (fetched).

**B14. Direct, on-point industry precedent for "review comments become durable rules" — the
specific out-of-band case in the question.** A 2607.13091 paper ("Self-Improving AI Coding Agents
Through Accumulated Behavioral Rules: A Closed-Loop Framework") describes exactly the mechanism
echo would need for code-review feedback: "every accepted review comment is codified as a
persistent behavioral rule, progressively expanding the set of error classes the agent can
self-detect." Rules are stored in "a version-controlled instruction file" (i.e. a plain file
committed to the repo, not a vector store) alongside a generated "self-review checklist," with
"automated validation that ensures rule set integrity as it grows" (their deployment accumulated
18 behavioral rules, 15+ language-specific standards, and a 15-item checklist). Recall is: before
submitting code, the agent runs the self-review checklist derived from the accumulated rules. The
paper reports "a measured 0% recurrence rate for ruled-against error classes" and frames this as
"persistent cross-session learning without weight updates" — i.e. review feedback is written back
as an explicit, versioned, human-readable rule file rather than fine-tuning or a vector store.
Source: https://arxiv.org/abs/2607.13091 (fetched).

**B15. The general "out-of-band learning" pattern across B8, B13, B14.** Three independent,
concretely-sourced mechanisms converge on the same shape for capturing knowledge that never
appears in a spec: (1) something happens outside the plan (a human correction, a review comment, a
test/eval failure); (2) a model-driven step turns that raw event into a short, generalized,
written statement (a "reflection," a "behavioral rule," a "suggested Knowledge item"); (3) a
human or an automated validator can accept/edit/reject that write before it becomes durable
(Devin's edit/dismiss step, the closed-loop paper's "accepted review comment," Reflexion's
evaluator-gated write); (4) the durable form is a small, versioned, human-readable artifact (a
rule file, a knowledge item, a memory file) rather than raw logs, and it is recalled by a
trigger/checklist mechanism at the point of doing new work, not by loading the whole history.
Source: inference synthesizing B8, B13, B14 (each individually sourced above).

### Risks and unknowns

- I could not directly fetch Cursor's own `docs.cursor.com/context/memories` page (it 308-redirected
  to `cursor.com/docs`, a different, more general page) or Letta's/Windsurf's/GitHub's memory pages
  directly; those findings (B3, B4 second half, B7, B10) rest on WebSearch result snippets rather
  than a page I fetched myself. They are internally consistent with each other and with sources I
  did fetch, but should be treated as secondary until independently re-verified against the primary
  page if this becomes load-bearing for a build decision.
- The Generative Agents mechanism (B12) is likewise from a WebSearch snippet, not the primary paper
  text, because the ACM full-text URL returned HTTP 403. The mechanism described (recency +
  relevance + importance weighting) is widely and consistently cited elsewhere, so I judge it
  reliable, but it is not a first-hand fetch.
- The community blog used for A12/B (giuseppegurgone.com) is not an Anthropic document; its claims
  about a specific internal feature-flag name (`tengu_coral_fern`) and the exact 200-line limit
  are unverifiable against an official source and should be treated as unverified detail, not fact.
  What I verified first-hand in this same session (A11) is only: the index file's content was
  injected into this session's context, and a per-fact file required an explicit Read (i.e. was not
  pre-loaded), with a staleness warning attached on read.
- I did not check whether any Jira MCP tool, when available, already exposes a way to search past
  tickets' comments/descriptions across the whole project (which could itself be a cross-ticket
  recall channel for echo, orthogonal to `.echo/`). No Jira/Confluence MCP tool was invoked in this
  research session, so this is an open unknown, not a checked "no."
- I did not exhaustively read every `bin/echo-*` script byte-for-byte (e.g. `echo-git`,
  `echo-install-hooks`, `echo-plan-guard`, `echo-verify-gate`) since a targeted grep and read of the
  memory-relevant ones (`echo-capture`, `echo-recall`, `echo-watch`, `echo-verify`) plus
  `echo_common.py` was sufficient to answer the memory question; it remains possible (though I found
  no grep evidence) that one of the unread scripts has an undiscovered cross-ticket reference.

## Options and tradeoffs

These are Part C: concrete design options for echo's own global memory, given the stdlib-only,
JSON-state, "determinism in bin/, prose is model-driven" constraint from this repo's CLAUDE.md.
Labeled as recommendation/inference throughout; none of this is implemented or decided.

**Option 1 — Mirror the harness's own pattern: a `.echo/memory/` index + per-fact files.**
A `MEMORY.md`-equivalent (`.echo/memory/index.md`, plain markdown, small, always read by
`echo-recall`) holding one-line pointers to per-fact files (`.echo/memory/<slug>.md`), each with a
short "why / how to apply" body, written by a model step (not `bin/`, per the repo's own
determinism boundary) when a ticket reaches `done` or when a maker-checker/review loop surfaces a
generalizable lesson. `echo-recall` would load the index (small, bounded) every session, same as
today's recap; per-fact files are read on demand (by the model, via the Read tool it already has),
mirroring B2's "just-in-time" pattern and the harness's own A11 design, not vector search.
- For: matches a design already validated next to this exact repo (A11); stdlib-only (plain
  markdown/JSON, no vector DB); the index-vs-fact-file split keeps `echo-recall`'s output bounded
  the same way `RECAP_MAX` already bounds recap.md (echo/bin/echo-recall:14).
  Determinism boundary preserved: `bin/` only reads/writes the index file structurally (append a
  pointer line, same as `set-artifact` today); the prose content of each fact file is model-written,
  same split the repo already uses for intent/spec/plan (echo's own CLAUDE.md: "prose generation is
  model-driven").
- Against: needs curation discipline (staleness, duplicate facts) that the harness's own version
  handles by human/model judgment, not code — echo would need to decide who/what prunes or marks a
  memory stale (see Open questions). Also needs a decision on where the write is triggered from
  (which stage, which hook) since nothing today writes prose except stage artifacts.
  This entire option is inference; no prototype was built.

**Option 2 — Derive a global rollup from `episodes.jsonl` (already collected, currently unread).**
Since `episodes.jsonl` already accumulates a cross-ticket, append-only fact log (A6) written
deterministically by `bin/echo-capture`, a new deterministic `bin/echo-*` command could summarize
it (e.g. "last N tickets, their final stage, branch, commit") into a small, bounded, `bin/`-owned
markdown or JSON rollup that `echo-recall` also surfaces. This requires no new write trigger
because the facts are already being captured.
- For: zero new write-path design; purely reads data that already exists; stays fully in the
  deterministic `bin/` layer (no model-authored prose needed for the rollup itself); cheap to add
  incrementally.
- Against: `episodes.jsonl` entries are thin (ticket, stage, branch, commit, changed files) — no
  decisions, no "why," no review feedback, no lessons. This closes the "cross-ticket awareness of
  what happened" gap but not the "cross-ticket awareness of *why* a decision was made" or the
  "out-of-band learning" (review comments, CI failures) gap, since those are captured elsewhere
  (`.echo/verify/`, Jira comments) and are not in `episodes.jsonl` at all (A8).
  This entire option is inference; no prototype was built.

**Option 3 — Cross-ticket artifact indexing (search prior intent/spec/plan by keyword).**
A deterministic `bin/echo-search` (or a flag on `echo-stage`) that greps/indexes all
`.echo/artifacts/*/*.md` (and `.echo/review/*.md`, `.echo/verify/*.md`) for a keyword/topic the new
intent stage supplies, returning matching file:line snippets the model can then choose to read in
full. This is closer to Option 1 of the harness's memory tool (B2) in spirit — "read back the
actual project files on demand" — but skips writing anything new; it treats the artifacts that
already exist as the memory corpus.
- For: no new write path or curation problem at all — the corpus is exactly what already exists
  and is already committed/versioned in git; fully stdlib (subprocess `grep`/`git grep`, no
  indexing infra); directly answers "what did a prior ticket decide" from primary sources rather
  than a paraphrased memory file (avoiding the "confabulation"/staleness risk noted in B2's docs
  and this session's own memory staleness reminder, A11).
- Against: does not solve the "out-of-band learning" half of the question at all — a review comment
  or CI failure that was fixed and then discarded (A8: `.echo/verify/*.md` is overwritten each run,
  never given a persistent home) leaves no artifact to index. Recall quality depends entirely on
  keyword match, not curated relevance; could surface a lot of noise on a large history.
  This entire option is inference; no prototype was built.

A combination is plausible and is itself inference: Option 3 (index existing per-ticket artifacts,
cheap and needs no new write path) for "what did we decide before," plus a narrow slice of Option 1
(one small write trigger, specifically for out-of-band events: an accepted review comment or a
repeated CI/test failure becomes one short fact-file, closest to B14's "accepted review comment ->
persistent rule" mechanism) for "what did we learn the hard way." Option 2 is the lowest-effort
partial step and could be built first as a floor under either of the others.

## Open questions for the intent stage (all inference/recommendation, not decided here)

- **Scope of memory**: repo-wide (all tickets in this `.echo/`) or per-component/module? Given
  echo is a single-developer, single-repo tool today (this repo's own CLAUDE.md: "for a single
  developer"), repo-wide is the natural default, but this is a judgment call, not a fact.
- **Write triggers**: which events write to global memory — every ticket reaching `done`
  (comparable to the harness's own "session end" trigger, A11), only maker-checker/critic findings
  that recur, only human-approved review comments (B14's "accepted" gate), only CI failures that
  repeat more than once? Echo currently has approval gates it could reuse as the "accept" step
  (`echo-stage approve`, referenced throughout `commands/*.md`), which would answer B14's "who
  approves the write" question for free if reused.
- **Out-of-band write path specifically**: today `bin/echo-watch` and `commands/review.md` surface
  CI failures and review comments to the human/Jira but write nothing durable past the next
  overwrite (A8). Deciding whether these become memory writes (and through what approval step) is
  the crux of the second sub-question in this research and is unresolved here by design.
- **Recall mechanism**: always-injected small index (mirrors `echo-recall`'s existing `RECAP_MAX`
  pattern, Option 1) vs. on-demand search (Option 3) vs. both. Given echo already has exactly one
  bounded, always-injected artifact (`recap.md` capped by `RECAP_MAX`), extending that same
  bounded-injection pattern is the path of least new design, but that is a recommendation, not a
  finding.
- **Staleness/curation**: who marks a memory fact wrong or stale, and when? The harness's own
  design (A11) attaches an automatic "N days old, verify against current code" warning on every
  read of a per-fact file, rather than deleting or requiring manual pruning — that specific
  mechanism (a read-time staleness disclaimer rather than active curation) is a candidate pattern
  worth carrying into echo's own design, but adopting it is a recommendation.
- **Determinism boundary**: per this repo's own architecture rule ("determinism lives in
  `bin/`/`lib/`; only prose generation is model-driven," this repo's CLAUDE.md, and
  echo_common.py's own module docstring at line 1-6), any global-memory feature must keep file I/O,
  path resolution, and structural edits (e.g. "append a pointer line to the index") inside `bin/`,
  while the actual lesson/fact text stays model-authored — exactly the same split intent/spec/plan
  already use. This is a hard constraint to carry forward, not a choice.

## Recommendation

Not enough evidence exists yet to pick a single final design, and this document intentionally does
not decide one; that decision belongs to the intent/spec stage. What the evidence does support,
concretely:

1. The gap is real and precisely bounded (A1-A9): echo has an append-only cross-ticket fact log
   already (`episodes.jsonl`) that nothing reads, and per-ticket artifacts that nothing
   cross-references; both are additive gaps, not redesigns.
2. The lowest-risk first step is Option 2 (surface `episodes.jsonl` as a bounded rollup) because it
   needs no new write trigger, stays fully deterministic, and directly extends a pattern
   (`echo-recall` reading a small bounded summary) that already exists and already works
   (A7, and `RECAP_MAX` at echo/bin/echo-recall:14).
3. For the out-of-band half of the question specifically, the industry's most directly-transferable,
   primary-sourced mechanism is B14 (review comment -> approved -> versioned rule file, checked at
   the point of doing new work) combined with B13's evaluator-gated write (Reflexion): both put a
   human/automated *acceptance* step between "something happened" and "it becomes a permanent
   memory," which maps cleanly onto echo's existing approval-gate concept
   (`echo-stage approve`) rather than requiring new infrastructure.
4. The harness's own MEMORY.md + per-fact-file pattern (A11) is the closest working reference
   design *in this exact environment* and should be the starting template for Option 1 if the
   intent stage chooses that route, specifically because it is already proven to (a) stay small
   enough to always-inject, (b) separate a cheap index from richer per-fact files, and (c) attach a
   staleness warning rather than silently trusting old facts.

## Sources

- <repo-root>/lib/echo_common.py (paths, state, config, stages)
- <repo-root>/bin/echo-recall (SessionStart/PostCompact hook)
- <repo-root>/bin/echo-capture (Stop/SessionEnd hook: recap.md,
  episodes.jsonl)
- <repo-root>/bin/echo-watch (post-ship CI/review capture)
- <repo-root>/bin/echo-verify (test-run proof artifact)
- <repo-root>/hooks/hooks.json
- <repo-root>/commands/intent.md
- <repo-root>/commands/watch.md
- <repo-root>/commands/review.md
- <repo-root>/agents/critic.md
- <repo-root>/.echo/state.json (read directly)
- <repo-root>/.echo/recap.md (read directly)
- <repo-root>/.echo/episodes.jsonl (read directly, `wc -l` = 101)
- <repo-root>/.echo/config.json (read directly)
- <repo-root>/.echo/artifacts/FEAT-6833/ (`ls`, read directly)
- Command run: `grep -rn "episodes\|recap\|previous ticket\|prior ticket\|cross-ticket\|other
  ticket" commands/ agents/` (no matches)
- <local-claude-memory-root>/memory/MEMORY.md
  (read directly, this session)
- <local-claude-memory-root>/memory/FEAT-6833-research-bucket.md
  (read directly, this session)
- This conversation's own system reminders (organization/user/project CLAUDE.md contents, and the
  literal injected MEMORY.md text), used as a directly-observed primary source for the harness's
  memory-injection behavior
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool (fetched)
- https://docs.devin.ai/product-guides/knowledge (fetched)
- https://aider.chat/docs/usage/conventions.html (fetched)
- https://www.langchain.com/blog/langmem-sdk-launch (fetched)
- https://github.com/mem0ai/mem0 (fetched)
- https://arxiv.org/html/2303.11366 — Reflexion: Language Agents with Verbal Reinforcement Learning
  (fetched)
- https://arxiv.org/abs/2607.13091 — Self-Improving AI Coding Agents Through Accumulated
  Behavioral Rules: A Closed-Loop Framework (fetched)
- https://giuseppegurgone.com/claude-memory (fetched; third-party/unofficial, flagged)
- WebSearch result summaries (page not directly fetched, flagged as secondary in-line): Cursor
  Memories (docs.cursor.com/context/memories, redirected on fetch attempt), GitHub Copilot
  Agentic Memory (docs.github.com), OpenAI Codex Memories
  (developers.openai.com/codex/memories, redirected on fetch attempt), Windsurf Cascade Memories
  (docs.windsurf.com/windsurf/cascade/memories), Letta/MemGPT memory hierarchy
  (docs.letta.com/letta-memgpt), Generative Agents memory stream mechanism (Park et al. 2023,
  ACM full text returned HTTP 403 on direct fetch attempt)
