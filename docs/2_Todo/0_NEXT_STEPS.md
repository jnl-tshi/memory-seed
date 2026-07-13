# Next Steps

Status: Active implementation-run brief (2026-07-10 goal run complete; post-run work shipped)
Updated: 2026-07-13
Source: `docs/2_Todo/` active proposals, `docs/2_Todo/completed/` completed proposals,
`docs/3_Spec/functionality-audit.md`, the 2026-07-10 goal-run Phase 1 alignment audit
(three-agent plan review + user decisions), and
`goal-roadmap-refinement-and-staged-implementation.md`.

## Next Implementation Run Brief

This section is the current source of truth for the current goal run
(`goal-roadmap-refinement-and-staged-implementation.md`). Keep it small; older release history
below is retained for context only.

**Shipped since the 2026-07-08 brief (unreleased on `main`, pushed):** `session merge-branch`
one-step integration; typed `evolves`/`evolved_by` edges; structured `continuity:` artifact
lineage; rarity-weighted `F:` file-overlap suggest ranking with rename alias bridging;
`memory_search` freshness fields; session-log-check escalation hardening; fuse rewriter spacing
fix; authored-inverse-field append-only guard.

**Goal run COMPLETE 2026-07-10.** All approved stages shipped, one merge commit each (revert
`-m 1` of the merge backs a stage out):

| Stage | Work | Merge commit |
|---|---|---|
| S1 (Phase 2/3) | Doc/status repairs + review-swarm fixes | `aedd1c0`, `77c6c1b` (direct-main docs) |
| S2 | README hotfix: trace install truth + mojibake | `0d87ad9` |
| S3 | Lineage seeding pass (continuity/evolves/retirement entries) | `6ad3b33` |
| S4 | Core **2.17.0** cut + GitHub Release v2.17.0 (PyPI gate approved by user) | `20630fb` |
| S5 | Topics P1: vocabulary, parsing, filter, `topics list`/`check` | `f6291d5` |
| S6 | README front-door refresh (highlights, how-it-works, placeholders, links) | `1a09a3e` |

**Shipped since the goal run (2026-07-11/12, unreleased on `main` - see CHANGELOG Unreleased):**
Trace UI pass (Trail primary, search-as-function, relationship zone); versioned `/api/v1` contract +
Phase-0 harnesses; on-device worktree switcher; commit-accurate Trail merges from Memory-Entry
trailers (+ phantom trunk, Authored-in/Merged-by reader split); Trail lane color packs +
time-ordered lanes + lane-following indentation; lifecycle-edge link sidecars + `link audit` +
end-of-turn sweep; canonical entry-id tooling (`session entry-id` CLI, `memory_entry_id` MCP);
`session append` scaffolder + `session reorder` chronology repair (the 2026-07-12 misorder is
fixed - `session merge-branch` unblocked); `memory-seed esr` preflight; automatic Memory-Entry
trailers via the seeded `prepare-commit-msg` hook (+ `hooks install`, init default-on); serve-time
asset versioning + `--static-root`; browserless Trail golden-fixture regeneration. Follow-ups
carried forward:
historical lifecycle-edge backfill (declined 2026-07-12, revisitable now the sweep exists).

**Deferred out of this run:** `session-decision-diagrams-plan.md` Phase 3 export packs;
`related-entries-p2-mutation-plan.md`
historical curation writers (boundary with the seeding pass reconciled 2026-07-10 - typed
lifecycle history via seeding, untyped `related_entries` backfill via P2);
`memory-trace-ai-timeline-summarisation-plan.md`; `fontjoy-typography-pairing.md` (rides the next
Trace UI pass); the Trace lineage pass (evolves edges + continuity chains in Trail);
README screenshot captures to replace the S6 placeholders; decision-diagram
sidecar integration into Memory Trace views beyond the reader (deferred 2026-07-11 at user
direction - sidecars render only in the reader's "Decision diagrams" section today; candidate
shapes are a diagram indicator on Trail rows / Graph nodes, inline Trail expansion, or a
dedicated affordance, with scope to be designed with the user; see session entry
`mse_j4wn8rqk2t6x0vhs`).

**Memory Trace next-generation planning promoted 2026-07-11:** the top-level entry point is
[`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md),
with sequencing in
[`memory-trace-next-generation-implementation-roadmap.md`](memory-trace-next-generation-implementation-roadmap.md)
and coverage/retirement decisions in
[`memory-trace-next-generation-coverage-matrix.md`](memory-trace-next-generation-coverage-matrix.md).
The promoted specs are
[`../3_Spec/memory-trace-trail-search-and-graph-ux.md`](../3_Spec/memory-trace-trail-search-and-graph-ux.md)
and
[`../3_Spec/memory-trace-derived-artifact-provenance-contract.md`](../3_Spec/memory-trace-derived-artifact-provenance-contract.md).
Existing active implementation plans remain active where they own unique acceptance criteria:
distribution/publication, AI summarisation provider flow, topic Phase 4, and decision-diagram export
packs.

**Memory Trace release strategy revised and implemented 2026-07-12:** the UI keeps its separate
`memory-trace/` source/product boundary, but the install path is now `pip install
"memory-seed[trace]"` with the `memory-trace` command. Do not plan a separate `memory-trace` PyPI
project unless this strategy is explicitly reopened.

**Agent worktree namespace guard added 2026-07-12:** the active P1 proposal is
[`agent-worktree-namespace-guard-plan.md`](agent-worktree-namespace-guard-plan.md). It hardens the
multi-agent branch/worktree workflow so Codex, Claude, Gemini, Cursor, and configured third-party
agents can verify that write work is happening inside the correct agent-owned worktree namespace
before files are edited.

Continuity naming for new work:

- **Memory Seed**: core runtime, CLI, MCP, retrieval, validation, and session files.
- **Memory Trace**: companion package and human review UI.
- **Trail**: Memory Trace view for branch/supersession evolution.
- **Lense**: legacy compatibility name only.
- **Explorer**: historical working name only.

These items need user judgement, account access, or real-client validation.

## Active Roadmap

Approved 2026-06-13. Incremental release history has moved from 2.6.0 through the current 2.16.0
release. Source: docs/2_Todo review + session findings. `CHANGELOG.md` is the authority for what
shipped in which release; the summaries below are orientation only.

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
([`3.0-plan.md`](completed/3.0-plan.md)):

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

### Release 2.15.0 (shipped 2026-07-04)

Typed supersession edges P1, git commit <-> entry linking P1 (`Memory-Entry:` trailer +
`link commits`), ranking P1a/P1b (`inbound_relation_count`, dampened `importance_score`,
`connectivity` rename), and the `exclude_superseded` search filter. Full detail: `CHANGELOG.md`.

### Release 2.16.0 (shipped 2026-07-05)

Public retrieval service (`memory_seed/retrieval.py`, distribution plan Phase 1), entry-level
result rollup, decision-diagram sidecar surfacing through the shared service, the graph-edge
contract spec, risk-signaling skill, and Memory Trace graph `importance_score` sizing. Full
detail: `CHANGELOG.md`.

### Release 2.17.0 (cut 2026-07-10, goal-run S4)

`CHANGELOG.md`'s `## 2.17.0` section is the authority. Headlines: month-grouped session writes +
`migrate sessions-month-layout`; branch-session fuse + `session merge-branch` one-step
integration; typed `evolves`/`continuity` lifecycle edges with lifecycle-aware ranking and search
freshness fields; authoring-loop MCP tools; `branch status`; session-log-check escalation; UTF-8
encoding check/repair; process shutdown/upgrade commands; agent-selection init; proposal-lifecycle
and skill-architecture governance skills; Memory Trace source extraction (`memory-trace/` source
boundary, `lense` shim) and skill-profile CLI management. The release restores the
`.memory-seed/archive/<version>/` snapshot convention (dormant since 2.5). The older standalone
Trace PyPI workflow was retired when Trace moved to the root `memory-seed[trace]` extra.

### 3.0 - In Progress

See the reviewed, sequenced plan: [`3.0-plan.md`](completed/3.0-plan.md).

Multi-user Phases 1-2 shipped (2.9/2.10), the core multi-user increments (A-P3 integrity validation,
A-ID 80-bit entry IDs, A-P4 MCP metadata/filters, S2 participant registry parsing, and A-P5
`migrate sessions-layout`) shipped in 2.12.0, and related-entries generation P1 shipped in 2.13.0.
The 3.0 plan is now partly historical: shipped sections are retained for context. The Pillar B
distribution choice is implemented and merged on `main` as a separate `memory-trace/` source
boundary published through the root `memory-seed[trace]` optional extra;
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
2. **Pillar B Trace optional extra - implemented on `main`.** Memory Lense shipped in 2.13.0 as an
   in-package optional extra (`memory-seed[lense]`) - a V1 delivered inside the core package as a UI
   prototype vehicle. The source extraction is now implemented as `memory-trace/`, while the release
   path is `memory-seed[trace]` plus the `memory-trace` command. Plain `memory-seed` stays
   web-framework-free, `memory-seed lense` is a shim, and the separate `memory-trace` PyPI path is no
   longer active. Any future UI work consumes `build_related_entry_graph()` and the public retrieval
   service rather than forking graph or ranking logic.

Obsidian remains a UX inspiration or later integration, not the first implementation target.

Specs:

- [`codex/proposal-synergy-evaluation.md`](codex/proposal-synergy-evaluation.md) (current cross-proposal synthesis; use when deciding sequencing across logic capture, Trace graph work, fanout workflow, and render-verification ideas)
- [`Claude/proposal-synergy-evaluation.md`](Claude/proposal-synergy-evaluation.md) (independent, concurrent cross-proposal synthesis via 3-subagent fan-out; reconciled against the Codex pass above - see its "Reconciliation" section for what each pass caught that the other didn't)

- [`multi-user-session-memory-proposal.md`](completed/multi-user-session-memory-proposal.md) (completed - full scope shipped through 2.12.0)
- [`multi-user-deep-research-report.md`](completed/multi-user-deep-research-report.md) (completed - recommendations fully acted on)
- [`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md) (**active, canonical Memory Trace next-generation product/system entry point** - promoted 2026-07-11)
- [`memory-trace-next-generation-implementation-roadmap.md`](memory-trace-next-generation-implementation-roadmap.md) (**active** - phase sequence for API, React shell, Trail/search/graph parity, annotations, Evidence Packs, provider integrations, hosted foundations, and security)
- [`memory-trace-next-generation-coverage-matrix.md`](memory-trace-next-generation-coverage-matrix.md) (**active planning matrix** - explains which older plans remain active versus completed/reference)
- [`memory-trace-frontend-architecture-and-design-system-proposal.md`](memory-trace-frontend-architecture-and-design-system-proposal.md) (**active** - React/TypeScript/Vite design-system migration proposal, gated by parity fixtures and vanilla fallback)
- [`memory-trace-evidence-annotations-and-projection-architecture.md`](memory-trace-evidence-annotations-and-projection-architecture.md) (**active** - Evidence Packs, deterministic anchors, append-only annotations, projection architecture, and provider freshness)
- [`memory-trace-commercialisation-and-monetisation-report.md`](memory-trace-commercialisation-and-monetisation-report.md) (**active strategy** - free local Trail, paid advanced analysis/cross-project/hosted/managed-AI/enterprise tiers, validation still required)
- [`memory-trace-hosted-product-and-security-architecture.md`](memory-trace-hosted-product-and-security-architecture.md) (**active later-stage architecture** - hosted/team security, sync, entitlements, provider integration, and audit model)
- [`memory-trace-distribution-plan.md`](memory-trace-distribution-plan.md) (**active, canonical** - Phase 1 retrieval service, Trace source extraction, and the root `memory-seed[trace]` packaging fold-in are implemented; active only for no-default-web-dependency, shim, and release-documentation follow-through)
- [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md) (**active** - Phases 1-2 implemented in the unpushed tree; Phase 3 report/handover pack remains gated)
- [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md) (**active** - approved 2026-07-05; controlled `link add` and explicit historical backfill for curated `related_entries`, sequenced after the lower-risk retrieval/diagram/risk-signaling work unless reprioritized)
- [`memory-trace-topic-neighbourhoods-plan.md`](memory-trace-topic-neighbourhoods-plan.md) (**active** - clarified 2026-07-08; `topics:` becomes the normal 1-3-topic field for meaningful entries, backed by project-local `.memory-seed/topics.yaml`)
- [`agent-worktree-namespace-guard-plan.md`](agent-worktree-namespace-guard-plan.md) (**active P1** - add CLI/MCP guardrails and collaboration-skill guidance so writing agents use their own `.codex/`, `.claude/`, `.gemini/`, or `.cursor/` worktree namespace)
- [`readme-front-door-refresh-plan.md`](completed/readme-front-door-refresh-plan.md) (**implemented 2026-07-10** via goal-run S2 hotfix + S6 refresh; residual: real screenshots/GIFs replace the placeholders when captured, optional tail-slimming into docs/)
- [`evolution-edges-plan.md`](evolution-edges-plan.md) (**P1 implemented 2026-07-10, unreleased** - typed `evolves`/`evolved_by` edge, append-only inverse enforcement, structured `continuity:` artifact lineage, rarity-weighted `F:` file-overlap ranking with alias bridging, and `memory_search` freshness fields all shipped with tests; remaining: the user-reviewed lineage seeding pass and the deferred Trace lineage pass)
- [`user-interface-deep-research-report.md`](completed/user-interface-deep-research-report.md) (completed 2026-07-05 - historical research; its one live tail, the Pillar B decision, was made and split into the distribution plan above; citation artifacts scrubbed 2026-07-05)

- [`completed/memory-explorer-entry-level-ui-results-plan.md`](completed/memory-explorer-entry-level-ui-results-plan.md) (**completed 2026-07-06** - entries are selectable results; subsection matches are highlighted inside the parent entry)
- [`completed/memory-trace-product-and-trail-view-plan.md`](completed/memory-trace-product-and-trail-view-plan.md) (**completed 2026-07-06** - Memory Trace is the package/product, Trail is the branch/supersession evolution view)
- [`completed/risk-signaling-and-stop-triggers-plan.md`](completed/risk-signaling-and-stop-triggers-plan.md) (**implemented 2026-07-05, unreleased** - consolidates confidence signaling and STOP-trigger guidance into one lazy-loaded risk skill before mutation/automation work)
- [`completed/memory-seed-utf8-encoding-policy-phase-1.md`](completed/memory-seed-utf8-encoding-policy-phase-1.md) (**completed 2026-07-07, unreleased** - UTF-8/LF/NFC policy, repo config, helper, docs, MCP Unicode output, and regression tests)
- [`completed/utf8-encoding-doctor-and-static-check-plan.md`](completed/utf8-encoding-doctor-and-static-check-plan.md) (**completed 2026-07-08, unreleased** - checker/repair/static enforcement follow-up split from the completed Phase 1 work)
- [`completed/memory-seed-trace-upgrade-shutdown-plan.md`](completed/memory-seed-trace-upgrade-shutdown-plan.md) (**completed 2026-07-08, unreleased** - conservative process shutdown and package-manager-aware upgrade workflow for Memory Seed and Memory Trace)

### Proposal Priority Order

P0 - **Roadmap hygiene and shared contracts.** Keep the coordinating docs current, resolve stale
3.0/UI status, fix audit counts/labels, and keep the shared graph/validation contract aligned for
`related_entries`, `supersedes`, `commits`, `inbound_relation_count`, and `importance_score`.

P1 - **Low-risk guidance and graph semantics.** Failed-approaches logging, Mermaid usage guidance,
the fanout collaboration recipe, `supersedes` P1, git commit linking P1, and ranking P1a/P1b have
all shipped or are queued in unreleased commits.

P1a - **Agent worktree namespace guard.** Active 2026-07-12. Add a pre-write guard and MCP readout
so each writing agent can confirm it is in its own namespace before edits, while root checkout writes
require an explicit override.

P2 - **Read-only surfacing before behavior changes.** Expose raw `inbound_relation_count`, commit
metadata, and later `importance_score` as inspectable metadata before any default search-ranking
changes.

P2a - **Encoding hardening follow-up - implemented 2026-07-08 (unreleased).** Phase 1's
policy/helper layer now has check/repair commands, static implicit-I/O enforcement, backup-first
atomic safe repair, and non-fatal doctor integration.

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
