# Next Steps

Status: Active implementation-run brief
Updated: 2026-07-08
Source: `docs/2_Todo/` active proposals, `docs/2_Todo/completed/` completed proposals,
`docs/3_Spec/functionality-audit.md`, the 2026-07-07/2026-07-08 session entries, and the
2026-07-08 inbox triage.

## Next Implementation Run Brief

This section is the current source of truth for the next implementation run. Keep it small; older
release history below is retained for context only.

| Priority | Proposal | Why This Order |
|---|---|---|
| P0 | `utf8-encoding-doctor-and-static-check-plan.md` | Add repair + static implicit-I/O enforcement after the read-only `encoding check` scanner and active-tree mojibake repair. |
| P1 | `memory-trace-distribution-plan.md` | Finish release-ordering/publication follow-through: core 2.17 before `memory-trace 0.1.0`. |
| P2 | `memory-trace-topic-neighbourhoods-plan.md` | Implement core per-project topic indexes and 1-3 indexed `topics:` per meaningful entry, while keeping Trace's tag/context topics as fallback for old entries. |
| P3 | `readme-front-door-refresh-plan.md` | Polish launch-facing docs once the release-safety and Trace packaging blockers are settled. |

Immediate implementation target:

1. Complete P0 if the goal is hardening before release.
2. Complete P1 if release ordering/publication is the next blocker.
3. P2 is now clarified and implementation-ready, but should still follow P0-P1 unless graph/topic
   memory becomes the immediate blocker.

Active but not in the next small run unless reprioritized:

- `session-decision-diagrams-plan.md` Phase 3 export packs.
- `related-entries-p2-mutation-plan.md` historical curation writers.
- `memory-trace-ai-timeline-summarisation-plan.md` AI-assisted evidence-pack summaries.
- `readme-front-door-refresh-plan.md` launch-documentation polish.

Continuity naming for new work:

- **Memory Seed**: core runtime, CLI, MCP, retrieval, validation, and session files.
- **Memory Trace**: companion package and human review UI.
- **Trail**: Memory Trace view for branch/supersession evolution.
- **Lense**: legacy compatibility name only.
- **Explorer**: historical working name only.

These items need user judgement, account access, or real-client validation.

## Active Roadmap

Approved 2026-06-13. Incremental release history has moved from 2.6.0 through the current 2.14.0
release. Source: docs/2_Todo review + session findings.

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

- **Memory Trace UI baseline (legacy Lense V1):** `memory-seed lense` serves as a deprecated
  compatibility route to the Memory Trace browser UI
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
  Memory Trace graph-node naming from `related_degree` to `connectivity`.
- **Proposal lifecycle skill:** `proposal_lifecycle.md` now defines inbox -> todo -> completed
  movement, reference/spec lanes, status requirements, completed-proposal movement rules, and required
  roadmap/audit update surfaces.
- **Worktree dependency strategy P1:** dependency tiers, task-packet dependency fields,
  orchestrator-owned dependency/lockfile policy, and the tmux control-room note now live in
  `agent_collaboration.md`.
- **Public retrieval service (Memory Trace distribution Phase 1):** `memory_seed/retrieval.py` owns
  search orchestration and the canonical result dicts; MCP is a thin parity-tested wrapper; the
  Trace consumes the same service.
- **Entry-level result rollup:** the shared `EntryRollup` contract collapses section matches into one
  selectable entry-level result with `best_match_chunk_id`/`matched_sections`/`score_source`
  highlight metadata; Memory Trace entry-granularity search consumes it; MCP and section/all granularities
  unchanged.
- **Session decision diagrams Phase 1:** `sessions/diagrams/YYYY-MM-DD.md` sidecars (one dated file
  per day, mirroring session-log filenames; each diagram a heading block naming its `entry_id`)
  validated by `links check` (`malformed-diagram`/`orphan-diagram`/`diagram-date-mismatch`), surfaced
  via `entry_diagram_sidecars()` + opt-in `get_chunk(include_diagrams=True)` + Memory Trace chunk metadata,
  with authoring guidance in `session_logging.md`/`end_of_turn.md` (live + seed).
- **Memory Trace extraction and Arc 2 UI work:** the review UI has been extracted into the standalone
  `memory-trace/` distribution, with `memory-seed lense` now a shim. Memory Trace includes reader
  subsection highlighting, Trail view (branch lineage + supersedes edges), design-token/microcopy
  baseline, and built-in client-side Mermaid rendering with source fallback.
- **Skill profiles and CLI skill management:** fresh projects install core skills by default,
  optional profiles can be selected during `init`, ignored optional skills stay ignored on `update`,
  and `memory-seed skills list|ignored|add|remove` rewires skill files and registry entries.
- **Reference-doc lifecycle:** `docs/4_Reference/` now holds source research and extracted learnings
  that inform proposals without remaining as actionable inbox/todo items; the planning profile creates
  the generic bootstrap anchors `docs/inbox/`, `docs/todo/`, `docs/todo/completed/`, and
  `docs/reference/` for newly initialized projects.
- **Compact diagramming skill:** `compact_mermaid_diagrams.md` is seeded and registered, covering
  compact rectangular Mermaid layout plus Mermaid-first/D2-specialist selection guidance.
- **UTF-8 encoding policy Phase 1 + checker slice:** `.editorconfig`, `.gitattributes`,
  `memory_seed.text_files`, README policy, generated-write hardening, MCP Unicode output, non-ASCII
  round-trip tests, and `memory-seed encoding check` are implemented. Follow-up remains active for
  `encoding repair` and static implicit-I/O enforcement.
- **Safe shutdown/upgrade workflow proposal:** completed for `memory-seed` and `memory-trace`;
  process discovery, dry-run previews, JSON output, confirmation-gated shutdown, failed-shutdown
  upgrade blocking, manager selection/detection, and `uv`/`pipx`/`pip` upgrade command execution are
  implemented.

### 3.0 - In Progress

See the reviewed, sequenced plan: [`3.0-plan.md`](3.0-plan.md).

Multi-user Phases 1-2 shipped (2.9/2.10), the core multi-user increments (A-P3 integrity validation,
A-ID 80-bit entry IDs, A-P4 MCP metadata/filters, S2 participant registry parsing, and A-P5
`migrate sessions-layout`) shipped in 2.12.0, and related-entries generation P1 shipped in 2.13.0.
The 3.0 plan is now partly historical: shipped sections are retained for context. The Pillar B
distribution choice is implemented in the unpushed tree as the standalone `memory-trace/` package;
see [`memory-trace-distribution-plan.md`](memory-trace-distribution-plan.md). The Memory Trace
product and Trail view plan is completed at
[`completed/memory-trace-product-and-trail-view-plan.md`](completed/memory-trace-product-and-trail-view-plan.md).
Related-entries P2 is approved and scoped in
[`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md), but should sequence
after the lower-risk retrieval-service and decision-diagram work unless reprioritized. The shared
graph-edge contract across CLI/MCP/Trace surfaces is written up in
[`../3_Spec/graph-edge-contract.md`](../3_Spec/graph-edge-contract.md).
Remaining work:

1. **Related-entries generation P2 (approved 2026-07-05; sequence after Phase 1 unless reprioritized).** P1 (`memory-seed link suggest` +
   `memory-seed link show` + `build_related_entry_graph()`, bidirectional read-time traversal) is
   released as of 2.13.0. Scope, decisions, and the deferred P2 are in
   [`related-entries-generation-plan.md`](completed/related-entries-generation-plan.md); the active
   implementation scope is [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md).
   P2: backfilling edges between two pre-existing entries, and the optional `link add` writer
   (current-entry-only) if hand-editing YAML proves painful. This is a convenience increment, not a
   blocker for graph read paths; existing YAML plus `link suggest`/`link show` already covers
   discovery and inspection.
2. **Pillar B separate-distribution - implemented in the unpushed tree.** Memory Lense shipped in
   2.13.0 as an in-package optional extra (`memory-seed[lense]`) - a V1 delivered inside the core
   package as a UI prototype vehicle. The companion package extraction is now implemented as
   `memory-trace/`: the package and command are `memory-trace`, core sheds the web stack, and
   `memory-seed lense` is a shim. Remaining: release core 2.17 before publishing
   `memory-trace 0.1.0`, because Trace depends on the new `branch:` field.
   Any future UI work consumes `build_related_entry_graph()` and the public retrieval service rather
   than forking graph or ranking logic.

Obsidian remains a UX inspiration or later integration, not the first implementation target.

Specs:

- [`codex/proposal-synergy-evaluation.md`](codex/proposal-synergy-evaluation.md) (current cross-proposal synthesis; use when deciding sequencing across logic capture, Trace graph work, fanout workflow, and render-verification ideas)
- [`Claude/proposal-synergy-evaluation.md`](Claude/proposal-synergy-evaluation.md) (independent, concurrent cross-proposal synthesis via 3-subagent fan-out; reconciled against the Codex pass above - see its "Reconciliation" section for what each pass caught that the other didn't)

- [`multi-user-session-memory-proposal.md`](completed/multi-user-session-memory-proposal.md) (completed - full scope shipped through 2.12.0)
- [`multi-user-deep-research-report.md`](completed/multi-user-deep-research-report.md) (completed - recommendations fully acted on)
- [`memory-trace-distribution-plan.md`](memory-trace-distribution-plan.md) (**active, canonical** - Phase 1 retrieval service and Phase 2 package extraction are implemented in the unpushed tree; active only for release-ordering/publication follow-through)
- [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md) (**active** - Phases 1-2 implemented in the unpushed tree; Phase 3 report/handover pack remains gated)
- [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md) (**active** - approved 2026-07-05; controlled `link add` and explicit historical backfill for curated `related_entries`, sequenced after the lower-risk retrieval/diagram/risk-signaling work unless reprioritized)
- [`memory-trace-topic-neighbourhoods-plan.md`](memory-trace-topic-neighbourhoods-plan.md) (**active** - clarified 2026-07-08; `topics:` becomes the normal 1-3-topic field for meaningful entries, backed by project-local `.memory-seed/topics.yaml`)
- [`readme-front-door-refresh-plan.md`](readme-front-door-refresh-plan.md) (**active** - clarified 2026-07-08; README refresh should include real screenshots/GIFs or placeholders)
- [`user-interface-deep-research-report.md`](completed/user-interface-deep-research-report.md) (completed 2026-07-05 - historical research; its one live tail, the Pillar B decision, was made and split into the distribution plan above; citation artifacts scrubbed 2026-07-05)

- [`completed/memory-explorer-entry-level-ui-results-plan.md`](completed/memory-explorer-entry-level-ui-results-plan.md) (**completed 2026-07-06** - entries are selectable results; subsection matches are highlighted inside the parent entry)
- [`completed/memory-trace-product-and-trail-view-plan.md`](completed/memory-trace-product-and-trail-view-plan.md) (**completed 2026-07-06** - Memory Trace is the package/product, Trail is the branch/supersession evolution view)
- [`completed/risk-signaling-and-stop-triggers-plan.md`](completed/risk-signaling-and-stop-triggers-plan.md) (**implemented 2026-07-05, unreleased** - consolidates confidence signaling and STOP-trigger guidance into one lazy-loaded risk skill before mutation/automation work)
- [`completed/memory-seed-utf8-encoding-policy-phase-1.md`](completed/memory-seed-utf8-encoding-policy-phase-1.md) (**completed 2026-07-07, unreleased** - UTF-8/LF/NFC policy, repo config, helper, docs, MCP Unicode output, and regression tests)
- [`utf8-encoding-doctor-and-static-check-plan.md`](utf8-encoding-doctor-and-static-check-plan.md) (**active** - checker/repair/static enforcement follow-up split from the completed Phase 1 work)
- [`completed/memory-seed-trace-upgrade-shutdown-plan.md`](completed/memory-seed-trace-upgrade-shutdown-plan.md) (**completed 2026-07-08, unreleased** - conservative process shutdown and package-manager-aware upgrade workflow for Memory Seed and Memory Trace)

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

P2a - **Encoding hardening follow-up.** Phase 1 shipped the policy/helper layer. The remaining
`encoding check/repair` and static implicit-I/O enforcement should land before broad user-facing
release if time allows, but it is not a blocker for the Trace extraction.

P2b - **Memory Trace product naming + Trail view gate - implemented 2026-07-06 (unreleased).** The
Trail-only product name is superseded; Memory Trace is the companion product/package/command, and
Trail is the internal branch/supersession evolution view.

P2c - **Memory Trace extraction + decision diagrams - implemented through Arc 2 (unreleased).** The
public retrieval service is extracted with MCP/Trace parity proven by tests, the entry-level result
rollup contract ships in the service, decision-diagram sidecars surface through the shared service,
Phase-1 diagram convention/validation/authoring guidance is live + seeded, and Trace renders the
supported diagram subset client-side.

P2d - **Risk signaling and STOP triggers - implemented 2026-07-05 (unreleased).** Qualitative Proceed/Proceed-and-flag/Propose-and-wait/Stop guidance now lives in the seeded `risk_signaling.md` lazy skill, with cross-references from collaboration and security triage. It remains guidance only: no new session schema and no automated gate.

P3 - **Parallel-work environment policy.** Worktree dependency tiers, dependency task-packet
fields, dependency-definition shared-file rules, and optional tmux control-room guidance shipped in
the collaboration skill 2026-07-05 (unreleased). Any scaffold remains deferred (see P4).

P4 - **Mutation and automation.** Related-entry backfill / `link add` is now approved and scoped in
[`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md), but remains behind the
Phase-1 retrieval/diagram work in sequencing. Continue to hold access-frequency telemetry, fanout CLI
scaffolding, worktree/dependency scaffolding, and render-verification automation until manual use
shows clear need and the privacy/retention/single-writer rules are settled.

P4a - **Optional AI summarisation.** Build deterministic evidence packs first, then local-model
summaries with mandatory citations. Terminal-agent adapters and external document/board exports stay
deferred until the read-only evidence-pack flow is stable.

### Logic Capture Improvements - Cluster fully resolved

Source: [`Memory-Seed Logic Capture Improvement.md`](completed/Memory-Seed%20Logic%20Capture%20Improvement.md)
(external review; moved to completed 2026-07-05 - all its actionable recommendations shipped via the
six plans below), evaluated against the current codebase and refined through discussion. All six
implementation docs live in `docs/2_Todo/completed/`; nothing from this cluster remains active.

1. [`git-commit-entry-linking-plan.md`](completed/git-commit-entry-linking-plan.md) - **P1 implemented
   2026-07-03 (unreleased):** the `Memory-Entry:` trailer convention, `commits:` schema field,
   git-gated `links check` validation, and read-only `memory-seed link commits` are built and
   tested. Remaining: the deferred P2 reminder-only post-commit hook.
2. [`supersession-edges-plan.md`](completed/supersession-edges-plan.md) - **P1 fully implemented 2026-07-03/04
   (unreleased):** the typed `supersedes` edge, read-time `superseded_by` inverse, `links check`
   validation (dangling/self/postdates/cycle guard), `link show`/`memory_get_chunk` exposure, and
   harmony-contract dampening are built and tested. Remaining: deferred P2 Memory Trace surfacing.
3. [`interaction-frequency-ranking-plan.md`](completed/interaction-frequency-ranking-plan.md) - **P1a + P1b
   implemented (unreleased):** raw `inbound_relation_count` and supersession-aware `importance_score`
   (dampened ×0.25 when superseded) exposed read-only via `link show` and `memory_get_chunk`; default
   ranking untouched. The Trace graph's combined-degree display field renamed to `connectivity` to resolve the
   name collision; Trace graph nodes now also carry `importance_score` with a "Size:" toggle. This
   also completed the supersession harmony contract. The commit-reference signal shipped 2026-07-04 as
   a standalone `commit_reference_count` field (not folded into `importance_score` - see
   `../3_Spec/graph-edge-contract.md`). Remaining: real access-frequency telemetry (Option B) is the deferred
   end goal.
4. [`mermaid-usage-guidance-plan.md`](completed/mermaid-usage-guidance-plan.md) - **implemented
   2026-07-03 (shipped 2.14):** the Working Principles bullet (plain text by default, Mermaid only for
   spatial/temporal/concurrent structure, semantic freshness included) is in `agent-rules.md` + seed
   twin.
5. [`failed-approaches-logging-plan.md`](completed/failed-approaches-logging-plan.md) - **implemented
   2026-07-03 (shipped 2.14):** the attempted-and-failed logging rule is in `session_logging.md`'s
   Reason Rules + seed twin.
6. [`exclude-superseded-filter-plan.md`](completed/exclude-superseded-filter-plan.md) - **implemented
   2026-07-04 (unreleased):** an opt-in `exclude_superseded` parameter on `memory_search` (default
   off) that drops entries with a non-empty `superseded_by` from that query only. Backend-only; no
   CLI/UI default. Surfaced during the 2026-07-03 synergy evaluation, not the original external review.

Items 1 and 2 shared a discovered dependency - `links check`'s dangling-`related_entries` validation
used to only run against per-user-day session files, not this repo's own legacy-flat layout - fixed
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

1. [`agent-fanout-workflow-plan.md`](completed/agent-fanout-workflow-plan.md) - the named "Fan-Out
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

### Worktree Dependency Strategy - Phase 1 implemented (2026-07-05, unreleased)

Source: an inbox proposal on worktrees, tmux, and dependency isolation, refined into
[`worktree-dependency-strategy-plan.md`](completed/worktree-dependency-strategy-plan.md).

1. Dependency tiers (`none`, `isolated`, `dependency-changing`) and the four dependency task-packet
   fields (`dependency_tier`, `dependency_setup`, `dependency_definition_policy`,
   `dependency_shared_cache_policy`) are in `agent_collaboration.md` (+ seed twin).
2. Dependency definition files and lockfiles are explicit orchestrator-owned shared files, escalated
   the same as control-plane files in Conflict Escalation.
3. A short optional tmux control-room note is in place: Git branches, worktrees, task packets,
   validation records, and handoff evidence remain the portable contract regardless of terminal tooling.
4. **Deferred, not blocking:** Phase 2 example task packets, and any `memory-seed workflow fanout`
   scaffold (Phase 3) as a preview-only, dry-run command - both wait on repeated manual validation.

### Seed Skill Promotions - Implemented (2026-07-05, unreleased)

Source: operational lessons from Windows DOCX rendering and verification work.

1. [`docx-render-windows-seed-lessons.md`](completed/docx-render-windows-seed-lessons.md) -
   **implemented 2026-07-05:** the universal lazy skill `docx_render_windows.md` ships in the seed
   (live + twin), registered in the trigger registry, cross-referenced from
   `office_document_editing.md`, and wired into `SEED_FILES`/package data/tests. Covers the
   LibreOffice profile-URI failure mode, bounded two-step render pattern, stale-process cleanup,
   Word field refresh, page-level visual QA, and the single-writer render / read-only validator
   boundary.

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
