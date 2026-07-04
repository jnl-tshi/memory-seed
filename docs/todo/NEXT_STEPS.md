# Next Steps

These items need user judgement, account access, or real-client validation.

## Active Roadmap

Approved 2026-06-13. Incremental release history has moved from 2.6.0 through the current 2.14.0
release. Source: docs/todo review + session findings.

### Release 2.6.0 (shipped 2026-06-13)

Bundles the SessionStart orientation hook (Claude/Codex/Gemini/Cursor) and Copilot CLI support, plus:

- **Gemini dead-wiring fix:** Gemini uses `AfterAgent` / `BeforeAgent`, not Claude-style
  `Stop` / `UserPromptSubmit`.
- **Copilot VS Code surface:** `.vscode/mcp.json` plus a thin `.github/copilot-instructions.md`
  router.
- **Hygiene:** current-state wording, recency-vs-topical retrieval guidance, and install docs.
- **Release mechanics:** 2.5 -> 2.6 package/control-plane bump, changelog, README, demo refresh,
  archive snapshot, and publish.

### Release 2.7.0 (shipped 2026-06-14)

- **Orphan & dead-artifact review:** diff-scoped orphan/artifact sweep added to the End Of Turn
  routine and mirrored in `/esr`; deterministic orphan-skill warning added to `doctor`.
- **Seed promotions:** `document_ingestion` and `office_document_editing` skills ported into the
  seed + live runtime with trigger-registry entries; Working Principles added to `agent-rules.md`.
- **ESR generalization:** later completed in 2.11.0.

### Release 2.8.0 (shipped 2026-06-14)

- **Non-destructive routing into foreign entry-point files:** routing files follow the greenfield /
  owned / foreign-with-markers / foreign-without-markers ownership branch in `init` and `update`.
- **Behavior change:** versionless entry-point files are merged, not overwritten.
- **Doctor route-presence backstop:** a `.memory-seed/` runtime whose present entry-point file is
  foreign-without-block is flagged as orphaned.

### Release 2.9.0 (shipped 2026-06-14)

- **Multi-user session dual-read discovery:** package readers discover both legacy flat files
  (`.memory-seed/sessions/YYYY-MM-DD.md`) and per-day/per-user files
  (`.memory-seed/sessions/YYYY-MM-DD/<user>.md`).

### Release 2.10.0 (shipped 2026-06-15)

- **User-aware session targets:** local user identity is opt-in through `.memory-seed/local.yaml`,
  `MEMORY_SEED_USER`, or `memory-seed session target --user`. New per-user targets are
  `.memory-seed/sessions/YYYY-MM-DD/<user>.md`.
- **User-aware hooks:** `session-log-check.py` checks only the active user's file, and
  `session-start-context.py` injects the active user's newest entry plus same-day co-contributor file
  counts.

### Release 2.11.0 (shipped 2026-06-15)

- **ESR generalization:** the End Of Turn routine now runs consolidation review and baseline-promotion
  checks. Seeded `/esr` command shortcuts ship for Claude and Gemini; Codex/Cursor use the routine in
  `agent-rules.md`.
- **Remaining optional:** seed `/esr` command shortcuts for Codex/Cursor once those tools support
  repo-level custom commands.

### Release 2.12.0 (shipped 2026-06-15)

First batch of multi-user Phase 3 increments from the reviewed 3.0 plan
([`3.0-plan.md`](3.0-plan.md)):

- **Session-memory integrity validation (A-P3):** `memory-seed links check` validates both layouts
  (duplicate `entry_id`/`hash_id`, dangling `related_*` refs incl. entry-level `related_entries`,
  per-user frontmatter user/date/schema/hash problems), names file + offending value, exits non-zero as
  a CI gate; `doctor` surfaces a one-line summary.
- **80-bit entry IDs (A-ID):** new generated `entry_id`s use deterministic `mse_` 80-bit Base32 IDs;
  legacy `ms-` IDs remain valid and are never rewritten.
- **MCP metadata + filters (A-P4):** `memory_search` / `memory_get_chunk` expose `session_date`, `path`,
  `user`, `file_hash_id`, and `related_entries`; `memory_search` filters by `user`, `date_from`, `date_to`.
- **Participant registry (S2):** `.memory-seed/project.yaml` supports a `participants:` list parsed
  fail-open and preserved across agent-selection writes.
- **Session-layout migration (A-P5):** `memory-seed migrate sessions-layout` splits legacy flat files
  into per-user files (`--dry-run`, ID-preserving, backup-before-remove, blocks ambiguous merges).
- **Schema doc:** the optional entry-level `related_entries` field is now documented in the
  `agent-rules.md` session-log schema.

### Release 2.13.0 (shipped 2026-07-01)

- **Memory Lense (in-package V1):** `memory-seed lense` serves a local FastAPI/Uvicorn browser UI
  (search, filters, timeline, graph, reader/details) backed by a rebuildable SQLite cache outside the
  repo. Install with `memory-seed[lense]`; without the extra the command prints an install hint. See
  the Pillar B note under 3.0 below for how this relates to the originally-planned separate
  distribution.
- **Related-entries generation P1:** `memory-seed link suggest`, `memory-seed link show`, and
  `build_related_entry_graph()` (bidirectional read-time traversal) are released.
- **Agent-rules lazy-skill extraction:** detailed procedures moved out of `agent-rules.md` into
  seeded skills (`history_retrieval.md`, `session_logging.md`, `end_of_turn.md`, `memory_hygiene.md`,
  `subproject_runtime.md`); `agent-rules.md` keeps startup-safe summaries and skill pointers.
- **New `agent_collaboration.md` skill** for Git-first subagent/branch/worktree/merge-conflict
  workflows.
- Packaging fix: every seeded file (ESR commands, hooks, document skills, new lazy skills) is now
  included in wheel/sdist package data.

### Release 2.14.0 (shipped 2026-07-03)

- **Participant-count session-layout gate:** configured solo users stay on the shared flat session
  file until `.memory-seed/project.yaml` lists 2+ participants.
- **One-time identity setup offer:** SessionStart suggests local identity setup once when none is
  configured, tracked by a gitignored stamp.
- **Doctor local-user warning:** `doctor` warns when a configured local user has no matching
  participant registry entry.
- **Legacy-flat links-check fix:** entry-level `related_entries` validation now runs for this repo's
  flat session layout as well as per-user/day files.
- **Working Principles / skill guidance:** decision-ladder and guard-preservation bullets, Mermaid
  usage guidance, failed-approach logging, and the Fan-Out Recipe in `agent_collaboration.md`.

### Unreleased after 2.14.0

- **Typed supersession edges P1:** `supersedes`, computed `superseded_by`, links-check guards, CLI
  and MCP exposure.
- **Git commit entry linking P1:** `Memory-Entry:` trailer, optional `commits:` field, git-gated
  validation, and `memory-seed link commits`.
- **Ranking P1a/P1b:** `inbound_relation_count`, supersession-aware `importance_score`, and the
  Memory Lense graph-node rename from `related_degree` to `connectivity`.
- **Proposal lifecycle skill:** `proposal_lifecycle.md` now defines the inbox -> todo -> completed
  document flow, status requirements, completed-proposal movement rules, and required roadmap/audit
  update surfaces.

### 3.0 - In Progress

See the reviewed, sequenced plan: [`3.0-plan.md`](3.0-plan.md).

Multi-user Phases 1-2 shipped (2.9/2.10), the core multi-user increments (A-P3 integrity validation,
A-ID 80-bit entry IDs, A-P4 MCP metadata/filters, S2 participant registry parsing, and A-P5
`migrate sessions-layout`) shipped in 2.12.0, and related-entries generation P1 shipped in 2.13.0.
The 3.0 plan is now partly historical: shipped sections are retained for context, while the active
3.0 decisions are related-entries P2, the Memory Lense/Pillar B distribution choice, and the shared
graph-edge contract between CLI/MCP/Lense surfaces.
Remaining work:

1. **Related-entries generation P2 (deferred, needs sign-off).** P1 (`memory-seed link suggest` +
   `memory-seed link show` + `build_related_entry_graph()`, bidirectional read-time traversal) is
   released as of 2.13.0. Scope, decisions, and the deferred P2 are in
   [`related-entries-generation-plan.md`](completed/related-entries-generation-plan.md).
   P2: backfilling edges between two pre-existing entries, and the optional `link add` writer
   (current-entry-only) if hand-editing YAML proves painful. This is a convenience increment, not a
   blocker for graph read paths; existing YAML plus `link suggest`/`link show` already covers
   discovery and inspection.
2. **Pillar B separate-distribution decision (still open).** Memory Lense shipped in 2.13.0 as an
   in-package optional extra (`memory-seed[lense]`) — a **V1 delivered inside the core package**, not
   the separate distribution `3.0-plan.md` originally decided on. It already covers B1 (local
   read-only service logic), B2 (search/filter/timeline/graph/reader UI), B3 (explainability: matched
   terms/fields, lexical/semantic scores, recency multiplier), and B4 (rebuildable SQLite cache,
   outside-repo, never authoritative). What remains **undecided**: whether to still spin Pillar B out
   into its own `memory-seed-explorer` distribution as originally planned, or keep iterating on the
   in-package extra instead. Any future UI work should consume `build_related_entry_graph()` rather
   than fork graph logic.

Obsidian remains a UX inspiration or later integration, not the first implementation target.

Specs:

- [`codex/proposal-synergy-evaluation.md`](codex/proposal-synergy-evaluation.md) (current cross-proposal synthesis; use when deciding sequencing across logic capture, Lense graph work, fanout workflow, and render-verification ideas)
- [`Claude/proposal-synergy-evaluation.md`](Claude/proposal-synergy-evaluation.md) (independent, concurrent cross-proposal synthesis via 3-subagent fan-out; reconciled against the Codex pass above — see its "Reconciliation" section for what each pass caught that the other didn't)

- [`multi-user-session-memory-proposal.md`](completed/multi-user-session-memory-proposal.md) (completed — full scope shipped through 2.12.0)
- [`multi-user-deep-research-report.md`](completed/multi-user-deep-research-report.md) (completed — recommendations fully acted on)
- [`user-interface-deep-research-report.md`](user-interface-deep-research-report.md) (still active — informed the shipped Memory Lense V1; the separate-distribution decision above remains open)

### Proposal Priority Order

P0 - **Roadmap hygiene and shared contracts.** Keep the coordinating docs current, resolve stale
3.0/UI status, fix audit counts/labels, and keep the shared graph/validation contract aligned for
`related_entries`, `supersedes`, `commits`, `inbound_relation_count`, and `importance_score`.

P1 - **Low-risk guidance and graph semantics.** Failed-approaches logging, Mermaid usage guidance,
the fanout collaboration recipe, `supersedes` P1, git commit linking P1, and ranking P1a/P1b have
all shipped or are queued in unreleased commits.

P2 - **Read-only surfacing before behavior changes.** Expose raw `inbound_relation_count`, commit
metadata, and later `importance_score` as inspectable metadata before any default search-ranking
changes.

P3 - **Parallel-work environment policy.** Add worktree dependency tiers, dependency task-packet
fields, dependency-definition shared-file rules, and optional tmux control-room guidance to the
collaboration skill before considering any scaffold.

P4 - **Deferred mutation and automation.** Hold related-entry backfill / `link add`, access-frequency
telemetry, fanout CLI scaffolding, worktree/dependency scaffolding, and render-verification
automation until manual use shows clear need and the privacy/retention/single-writer rules are
settled.

### Logic Capture Improvements - Current

Source: `Memory-Seed Logic Capture Improvement.md` (external review), evaluated against the current
codebase and refined through discussion. Five implementation docs now live in
`docs/todo/completed/`; the only active follow-on from this cluster is the opt-in
exclude-superseded filter.

1. [`git-commit-entry-linking-plan.md`](completed/git-commit-entry-linking-plan.md) — **P1 implemented
   2026-07-03 (unreleased):** the `Memory-Entry:` trailer convention, `commits:` schema field,
   git-gated `links check` validation, and read-only `memory-seed link commits` are built and
   tested. Remaining: the deferred P2 reminder-only post-commit hook.
2. [`supersession-edges-plan.md`](completed/supersession-edges-plan.md) — **P1 fully implemented 2026-07-03/04
   (unreleased):** the typed `supersedes` edge, read-time `superseded_by` inverse, `links check`
   validation (dangling/self/postdates/cycle guard), `link show`/`memory_get_chunk` exposure, and
   harmony-contract dampening are built and tested. Remaining: deferred P2 Lense surfacing.
3. [`interaction-frequency-ranking-plan.md`](completed/interaction-frequency-ranking-plan.md) — **P1a + P1b
   implemented (unreleased):** raw `inbound_relation_count` and supersession-aware `importance_score`
   (dampened ×0.25 when superseded) exposed read-only via `link show` and `memory_get_chunk`; default
   ranking untouched. Lense's combined-degree display field renamed to `connectivity` to resolve the
   name collision. This also completed the supersession harmony contract. Remaining: real
   access-frequency telemetry (Option B) is the deferred end goal; an optional commit-reference term
   on `importance_score` is unblocked but out of scope until there's a reason.
4. [`mermaid-usage-guidance-plan.md`](completed/mermaid-usage-guidance-plan.md) — **implemented
   2026-07-03 (shipped 2.14):** the Working Principles bullet (plain text by default, Mermaid only for
   spatial/temporal/concurrent structure, semantic freshness included) is in `agent-rules.md` + seed
   twin.
5. [`failed-approaches-logging-plan.md`](completed/failed-approaches-logging-plan.md) — **implemented
   2026-07-03 (shipped 2.14):** the attempted-and-failed logging rule is in `session_logging.md`'s
   Reason Rules + seed twin.
6. [`exclude-superseded-filter-plan.md`](completed/exclude-superseded-filter-plan.md) — **implemented
   2026-07-04 (unreleased):** an opt-in `exclude_superseded` parameter on `memory_search` (default
   off) that drops entries with a non-empty `superseded_by` from that query only. Backend-only; no
   CLI/UI default. Surfaced during the 2026-07-03 synergy evaluation, not the original external review.

Items 1 and 2 shared a discovered dependency — `links check`'s dangling-`related_entries` validation
used to only run against per-user-day session files, not this repo's own legacy-flat layout — fixed
2026-07-02 and shipped in 2.14. Both items are now unblocked; see either plan's "Known Dependency" section.

The sequencing dependency is now explicit: ship `supersedes` before any ranking surface claims to be
supersession-aware; keep `inbound_relation_count` as a raw read-only signal until then; treat
`commits:` as validated commit metadata before folding commit-backed terms into ranking or retrieval
explanations.
Failed approaches remain session-log evidence under `A`, not a new graph edge type.

### Agent Collaboration Workflow - Implemented (shipped 2.14)

Source: a user-uploaded multi-agent fanout/review workflow diagram, evaluated via a fan-out
research pass (3 subagents) plus an opus-tier critique, with the user resolving the one open
question raised. **Implemented 2026-07-03 and shipped in 2.14.**

1. [`agent-fanout-workflow-plan.md`](completed/agent-fanout-workflow-plan.md) — the named "Fan-Out
   Recipe: Explore / Plan / Implement / Validate" now lives in
   `.memory-seed/skills/agent_collaboration.md` (+ seed twin): the 9-gate pipeline (Scope,
   Exploration, Plan, Worker Identity, Worktree, Pre-Review Validation, Integration, a Bounded
   Review-to-Rework Loop capped at 2 iterations, Final Handoff), task-packet schema additions
   (`base_sha`, `expected_pwd`, `capability_tier`, `shared_file_policy`, `conflict_owner`,
   `review_loop`, `preflight`), and vendor-neutral capability-tier guidance (planning and review
   both warrant the top tier, not review alone).

The shipped increment is documentation and template guidance only. Any later CLI scaffold
must be preview-first/dry-run and emit task packets or checklists; it should not spawn agents,
coordinate worktrees, mutate branches, or edit shared memory directly. Worker agents contribute via
handoff summaries while the orchestrator remains the single writer for session logs, policy, index,
routing files, lockfiles, seed templates, and generated binaries unless explicitly delegated.

### Worktree Dependency Strategy - Proposed

Source: an inbox proposal on worktrees, tmux, and dependency isolation, refined into
[`worktree-dependency-strategy-plan.md`](worktree-dependency-strategy-plan.md). **Proposed, not yet
built.**

Priority: **P2 after the shipped Fan-Out Recipe and graph metadata work.** It directly improves the
safety of Codex/Claude/other-agent parallel work, but should remain documentation-first until manual
use proves a scaffold is worth adding.

1. Add dependency tiers (`none`, `isolated`, `dependency-changing`) and dependency task-packet fields
   to `agent_collaboration.md`.
2. Make dependency definition files and lockfiles explicit orchestrator-owned shared files.
3. Add a short optional tmux control-room note while keeping Git branches, worktrees, task packets,
   validation records, and handoff evidence as the portable contract.
4. Defer any `memory-seed workflow fanout` scaffold to a preview-only, dry-run command after repeated
   manual validation.

### Seed Skill Promotions - Proposed

Source: operational lessons from Windows DOCX rendering and verification work. **Proposed, not yet
decided or built.**

1. [`docx-render-windows-seed-lessons.md`](docx-render-windows-seed-lessons.md) - promote the
   Windows-safe DOCX render fallback and artifact hygiene lessons into reusable seed guidance,
   especially for document-rendering workflows where read-only fanout can inspect outputs but render
   mutation and cleanup should stay single-writer.

## MCP Client Validation

- Register Memory Seed in Claude Code or another MCP-capable client:

```powershell
claude mcp add memory-seed -s user -- uvx --from memory-seed memory-seed-mcp --stdio
```

- Ask the agent a question that should require historical project memory and confirm it calls
  `memory_search` before answering.
- Record any client-specific setup differences so the README can include confirmed examples.

## Launch Assets

- Capture a real terminal screenshot or short GIF showing `memory-seed init`,
  `memory-seed-mcp-validate`, and an agent memory lookup.
- Decide whether to publish a launch note focused on solo developers, teams standardizing agent
  memory, or both.

## Ranking Experiments

- Keep ranking behavior stable on `main`.
- Run ranking experiments on a separate branch and merge only if fixture tests show a clear improvement
  without degrading current text-ranking behavior.

## Optional Semantic Dependency

- Decide whether to add an optional package extra such as `memory-seed[semantic]` for Model2Vec-backed
  embeddings.
- Keep the default CLI and MCP path dependency-light unless the optional path shows clear value.

## Community Feedback

- Watch issue reports for agent compatibility gaps across Codex, Claude Code, Gemini CLI, and other
  MCP clients.
- Use the issue templates to separate bugs, feature requests, compatibility reports, and memory
  workflow improvements.
