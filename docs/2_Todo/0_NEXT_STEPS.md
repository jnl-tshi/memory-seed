# Next Steps

Status: **ACTIVE — Constitution-aligned** (v1.0 ratified 2026-07-14; v1.1 ratified 2026-07-16).
Updated: 2026-07-16

> ▶ **Foundation and memory-quality core shipped 2026-07-15.** The
> [derived-projection Phase 1](derived-projection-implementation-plan.md) (git-watermark warm start +
> atomic swap + three read-path perf refinements) **shipped 2026-07-15** — the plan's former "do first"
> foundation is done. Work still sequences *under* [`docs/CONSTITUTION.md`](../CONSTITUTION.md) **v1.1**
> (each item answers the five-question test — Capture / Validation / Retrieval / Trust / Application — and
> respects Invariant #6: Markdown = source of truth; every DB/cache is a derived, rebuildable projection).
> The ranking/graph core now includes the full-corpus gate, `superseding_head` plus its bounded boost,
> and inert `link audit --apply` scaffolding. The stated **2.19 cut criterion is met**; publishing still
> waits for explicit user approval. **B0a graph/workspace contracts and renderer evidence are complete;
> B2/B0b React parity is the current lead.** The projection's
> incremental-ingest fast-follow remains deferred as low-urgency (reads are already ~3.9 ms).
Source: the `docs/` lifecycle lanes (folder = state — see [`../README.md`](../README.md)), `CHANGELOG.md`,
and `docs/3_Spec/`. Rebuilt 2026-07-14 from a full inbox+todo evaluation; re-baselined 2026-07-15 after the
Foundation shipped (per-doc status verified against CHANGELOG + code, not this file's prior claims).

## Current state

- **Released: v2.18.0.** A large tranche is **shipped-but-unreleased on `main`** — see `CHANGELOG.md`
  "## Unreleased" for the authoritative list (highlights: DRAFT-format entry lint; `integration_mode`
  setting; freshness-aware `memory_search` ranking on by default + `evolved_head`; retrieve-the-*why*
  discipline; indexed `topics:` end-to-end incl. Trace rendering; decision-diagram badges in Trail/Graph;
  agent worktree namespace guard; MCP topic + sidecar-edge parity; hardened Memory-Entry trailer hook;
  `link show` now reflects the sidecar-augmented effective graph).
- **Foundation SHIPPED 2026-07-15:** derived-projection Phase 1 — git-watermark warm start (O(changes)
  freshness, no whole-corpus scan; ~6.2 s rebuild → ~78 ms warm) + atomic build/swap + schema version, plus
  three read-path perf refinements (freshness memoize, chunk memoize, sidecar-first-class freshness):
  `chunk()` 132 ms → 3.9 ms. Only the **incremental-ingest** fast-follow remains, deferred as low-urgency.
- **Doc lifecycle:** the folder a doc sits in *is* its state. This refresh moved the terminal docs into
  `5_Completed/` / `7_Superseded/` / `8_Deferred/`; only docs with live work remain in `2_Todo/`.
- **Wave 1 + closeout SHIPPED 2026-07-15:** `topics suggest --from`, deterministic timeline Evidence
  Packs, the Trail continuity axis, `superseding_head` plus the gated boost, all four configurable
  integration-mode phases, and lifecycle-link scaffold steps 1–3.
- **Release cadence:** the memory-quality trio has landed, so the stated **2.19 cut criterion is met**.
  Hold for the user's go on the release and PyPI push; publishing remains a manual-approval gate.

## Live work — sequenced (Constitution-aligned)

Active work, sequenced under the Constitution (each item answers the five-question test — Capture /
Validation / Retrieval / Trust / Application — and respects Invariant #6). The foundation and
memory-quality core shipped 2026-07-15, so **B0a graph/workspace work now leads**.

### Foundation — derived-projection Phase 1 ✅ SHIPPED 2026-07-15

**Made Trace fast + made Invariant #6 real.** The SQLite cache is now a formalized read-model per the
[contract](../3_Spec/draft/derived-read-model-projection-contract.md): explicit Markdown→projection ingest
with a byte-identical rebuild, a **git-watermark warm start** (O(changes) freshness — no whole-corpus scan)
and **atomic build/swap**, plus three read-path perf refinements (`chunk()` 132 ms → 3.9 ms). Plan:
[`derived-projection-implementation-plan.md`](derived-projection-implementation-plan.md). Five-question
test → **Retrieval** (fast reads) + **Application** (usable Trace on large histories).
**Remaining fast-follow (deferred, low-urgency):** *incremental ingest* — re-project only the delta files'
chunks and recompute whole-history git meta only when HEAD moved, gated behind an
`incremental == full-rebuild` equivalence test. Reads are already ~3.9 ms, so this waits until corpus scale
demands it. **Phase 2** (git-rooted historical integrity, G6/G7) is the next projection increment after the
trio.

### Ranking & graph quality — core SHIPPED 2026-07-15 (gate → surface → capture)

The memory-quality trio from the 2026-07-13 freshness-ranking session was approved, implemented in
dependency order, and closed on 2026-07-15:

1. **`ranking-ab` + the "expose before you rank" amendment** — ✅ **SHIPPED 2026-07-15**.
   [`real-corpus-ranking-validation-gate-proposal.md`](../5_Completed/real-corpus-ranking-validation-gate-proposal.md).
   The reusable `memory-seed ranking-ab` command and graph-edge-contract rule now require a full-corpus
   off/on comparison, intended directional wins, and an unchanged no-affected-hit control before a
   default ranking flip. Five-question → **Validation + Trust**. *The gate for item 2 now exists.*
2. **`superseding_head` + lineage-bounded replacement boost** — ✅ **SHIPPED 2026-07-15**.
   [`supersession-successor-surfacing-proposal.md`](../5_Completed/supersession-successor-surfacing-proposal.md).
   Additive successor exposure shipped first; the bounded boost then passed the full-corpus A/B gate.
   Five-question → **Retrieval + Trust**.
3. **`link audit --apply` sidecar scaffold, steps 1–3** — ✅ **SHIPPED 2026-07-15**.
   [`lifecycle-link-authoring-assist-proposal.md`](lifecycle-link-authoring-assist-proposal.md).
   Scaffolds inert `classify_pending` sidecar stubs, warns on unresolved stubs, and reports them in ESR.
   It never auto-classifies or emits a live edge; human classification remains mandatory. Optional steps
   4–5 are deferred while the shipped workflow is evaluated. Five-question → **Capture**.

### Track A — remaining open tails

1. **Related-entries P2** — [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md).
   Approved 2026-07-05, unbuilt: controlled `link add` (current-entry) + explicit historical backfill.
   It is a convenience increment, not a blocker.
2. **Session decision diagrams Phase 3** — [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md).
   Phases 1–2b shipped (sidecars, validation, reader + Trail/Graph badge & zoom viewer). Phase 3
   (exportable report / handover pack) is sizable and **gated on a product greenlight**.
3. **OpenSSF credibility** — [`openssf-credibility-proposals.md`](openssf-credibility-proposals.md).
   `SECURITY.md`, a CI gate, and G0–G2 remain approved-not-built. The configurable integration-mode
   foundation is complete, so this work is **unblocked**; adopting `integration_mode: pr` and branch
   protection still requires the documented project/user actions.
4. **Trace distribution — deprecation-window closeout** —
   [`memory-trace-distribution-plan.md`](memory-trace-distribution-plan.md). Both phases shipped (Phase 1
   released in 2.16.0; the optional-extra fold-in landed 2026-07-12), but the plan stays active for its
   last obligation: `memory-seed[lense]` and the `memory-seed lense` shim are a deprecated alias kept
   "for one release window," and that window is **still open** in `pyproject.toml`. **Open user decision:**
   whether 2.19 is the release that drops them. The coverage matrix
   ([`memory-trace-next-generation-coverage-matrix.md`](memory-trace-next-generation-coverage-matrix.md))
   records the optional-extra packaging, deprecation shim, and no-default-web-dependency criteria as owned
   by that plan — which is why it correctly remains in `2_Todo/`.

### Track B — Memory Trace next generation (the promoted direction, 2026-07-11)

Governance (read to sequence, not build): [`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md)
(entry point) → [`memory-trace-next-generation-implementation-roadmap.md`](memory-trace-next-generation-implementation-roadmap.md)
(Phase 0–10 spine; Phases 0–1 delivered) → [`memory-trace-next-generation-coverage-matrix.md`](memory-trace-next-generation-coverage-matrix.md).

- **B1 — Evidence Pack Builder** — ✅ **PHASE 1 SHIPPED 2026-07-15**.
  [`memory-trace-ai-timeline-summarisation-plan.md`](memory-trace-ai-timeline-summarisation-plan.md).
  `build_timeline_evidence_pack()` now emits deterministic, snapshot-tested JSON over the delivered
  retrieval/graph readers with **no write path and no provider**. The plan remains active for Phase 2: a
  disabled-by-default provider interface and local-model adapter whose cited generated output remains
  non-authoritative. The canonical shape is the spec
  [`../3_Spec/memory-trace-derived-artifact-provenance-contract.md`](../3_Spec/memory-trace-derived-artifact-provenance-contract.md)
  (blueprint §4.5 and the evidence-annotations doc are forward supersets — do not build a second builder).
- **B0a — Graph/workspace contract and benchmark** — **COMPLETE 2026-07-16** *(pre-React; JNL-endorsed
  2026-07-15; proposal set promoted 2026-07-15)*. The graph received semantic, interaction, and renderer
  attention before any React rebuild, without implementing the same UI twice.
  Sits **before B2**. Coordinating index:
  [`memory-trace-graph-and-workspace-proposal-set-index.md`](memory-trace-graph-and-workspace-proposal-set-index.md).
  B0a makes the decisions and produces the evidence B2/B0b must consume:
  1. **Shell behaviour / shared-selection contract** —
     [`memory-trace-three-region-workspace-and-dockable-inspector-proposal.md`](memory-trace-three-region-workspace-and-dockable-inspector-proposal.md):
     hamburger toggles only the left pane; Trail and Graph remain centre workspace modes; inspector
     visibility/dock state is independent. Apply only vanilla-safe clarifications that will not duplicate
     the React implementation.
  2. **Renderer-neutral graph contract + fixtures** —
     [`memory-trace-graph-visualisation-and-temporal-topology-proposal.md`](memory-trace-graph-visualisation-and-temporal-topology-proposal.md):
     separate graph semantics from renderer implementation while preserving the current SVG renderer as a
     fallback. The first bounded B0a fixture contract is now implemented in
     [`../3_Spec/memory-trace-renderer-neutral-graph-projection.md`](../3_Spec/memory-trace-renderer-neutral-graph-projection.md);
     the packaged side-by-side renderer harness completed its evidence sweep; JNL selected Cytoscape.js
     3.34.0 for B0b while retaining the SVG fallback.
  3. **Renderer benchmark** — the same bounded fixture passes the evidence sweep in vis-network and
     Cytoscape.js. Cytoscape.js is the selected B0b renderer.
  4. **Topology-first graph** — stable community colour, stronger node hierarchy, typed/curved edges,
     optional mild temporal drift, and bounded/community overview modes, specified and fixture-proven but
     not yet migrated to the selected renderer.
- **B2 — React/Vite shell** *(first implementation slice landed 2026-07-16)* —
  [`memory-trace-frontend-architecture-and-design-system-proposal.md`](memory-trace-frontend-architecture-and-design-system-proposal.md)
  (roadmap Phase 2). `memory-trace/client/` now builds a TypeScript React shell to packaged `/next` assets;
  it consumes only `/api/v1/*`, lazy-loads Cytoscape.js, and needs no Node.js at runtime. The first
  three-region shell has independent navigation and persisted Inspector dock state. Storybook, the formal
  Playwright harness, Trail/search parity, and accessibility acceptance remain open. The current vanilla
  `/` UI remains the supported fallback until explicit parity sign-off.
- **B0b — Native graph/workspace implementation** *(started 2026-07-16; implemented through roadmap
  Phases 3 and 5)* — the first React shell provides a lazy Cytoscape graph, bounded initial graph range,
  shared entry selection, right/bottom/auto/hidden persisted Inspector controls, and the additive
  `/api/v1/graph/projection` renderer-neutral contract. The React route now also has exact `mse_` and
  legacy `ms-` entry-ID navigation, ranked search results feeding shared Inspector selection, a recent
  seven-day default graph range with an explicit all-dates control, overview/local/topic filters, typed
  curved edges, selected-context `evolves` routes, focus/minimal/all label policy, keyboard fit/zoom/node
  cycling, and a complete-list alternative. Failed graph refreshes preserve the current view; graph mode
  renders connected context while the list retains unlinked records. Remaining: reader highlighting and
  evidence workspace, Trail transition/parity, file/evolution modes, evidence-backed topology communities
  and optional mild temporal layout, React diagram rendering, and formal accessibility/scale acceptance.
  Keep the SVG renderer until explicit parity sign-off.
  Only after B0b acceptance may the
  [`structural-provider proposal`](memory-trace-structural-graph-enrichment-provider-proposal.md) define a
  provider-neutral contract and pilot optional `code-review-graph`; providers never own canonical decision
  semantics or alter ranking without exposure and real-corpus validation.
- **BG1 — Provenance and authority taxonomy** *(constitutional gate before actionable annotations or
  agent-influencing generated output)* —
  [`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md).
  Extend the shipped seven-value `ProvenanceClass`; keep provenance, lifecycle, and actionability as
  separate fields; do not create a single trust score.
- **BG2 — Memory-quality metrics v0** *(read-only baseline; no ranking or automation effect)* —
  [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md). Define explicit
  populations and denominators for unlinked entries, DRAFT reason coverage, generated-claim citations,
  provenance coverage, and ranking A/B regressions. Measure the real corpus before setting targets.
- **B3 — Evidence annotations & projection** *(long-horizon, after B2/B0b and BG1)* —
  [`memory-trace-evidence-annotations-and-projection-architecture.md`](memory-trace-evidence-annotations-and-projection-architecture.md).
  Anchors, append-only annotations, SQLite projection — needs the React shell **and** a participant/role
  model first. No annotation becomes agent-actionable until BG1's authority rules are adopted.

### Track C — agent context efficiency (control-plane)

Approved + promoted 2026-07-14 from Inbox. Both P2, small, unblocked, independent of the Foundation and of
Tracks A/B — control-plane/skill/agent-rules guidance that slims how much context each agent loads. They
descend from the two-axis persona/orchestration evaluation (session `mse_y7nhd5hcpwa0qb51`):
"orchestrator/worker/reviewer" and "developer/copywriter" are *different axes*, so the real win is trimming
context, not renaming roles. Five-question test → **Application** (how agents load and apply memory);
Markdown-authoritative, so Invariant #6-clean (no derived-state surface).

1. **Worker Context Contract** — [`worker-context-minimisation-proposal.md`](worker-context-minimisation-proposal.md).
   A packeted subagent worker loads only its Task Packet + at most one domain persona + objective-triggered
   skills; it skips load-all-personas / full-index / newest-session read, but **still** runs
   `base_sha`/preflight/worktree-guard. Adds Task Packet fields `persona:` + `context_load:`. Guidance-only
   (`agent_collaboration.md`, `agent-rules.md`, seed twins).
2. **ESR Persona Usage Check** — [`persona-usage-deactivation-esr-proposal.md`](persona-usage-deactivation-esr-proposal.md).
   A new end-of-turn step, the symmetric inverse of the shipped unregistered-persona check: flag active
   personas with no recorded `agent_name` use over a conservative window and **propose** flipping them to
   `status: inactive` (approval-gated; never auto-applies; deactivate ≠ delete). **Open user decision:**
   propose-and-wait (designed) vs automatic deactivation — resolve before build.

The two compound (fewer active personas → lighter worker *and* primary startup load) but neither blocks the
other. Both sit **below Track A's open tails** in priority — small, sequence-flexible guidance changes.

### Track D — semantic memory and workflow evolution

Approved 2026-07-16 after full Inbox triage. These plans are dependency-ordered and do not displace B0b:

1. **Semantic record and signal foundation (P1)** —
   [`memory-seed-semantic-record-and-signal-foundation-plan.md`](memory-seed-semantic-record-and-signal-foundation-plan.md).
   After B0b plus BG1/BG2, prove authoritative append-only Markdown ADR sidecars on three real decisions.
   Entries retain rationale/evidence; the sidecar owns promotion/lifecycle; current status and indexes are
   derived. Historical entries are not rewritten and ranking cannot change before signal exposure plus the
   real-corpus gate.
2. **Workflow evidence and review workbench (P2)** —
   [`memory-seed-workflow-evidence-and-review-workbench-plan.md`](memory-seed-workflow-evidence-and-review-workbench-plan.md).
   Reconstruct three real idea-to-outcome journeys before defining a deterministic review queue. No raw
   telemetry, universal workflow, automatic judgement, or new generic graph edges.
3. **Semantic Trace projections (P3)** —
   [`memory-trace-semantic-projections-plan.md`](memory-trace-semantic-projections-plan.md). Begin with one
   validated Decision projection over shared readers; additional projections require user evidence.

The Evidence Envelope and Capability Status were folded into the existing evidence/annotations architecture.
The seeded document lifecycle was folded into the local lifecycle plan after its Phase 2/3 proof gates.
Publishability and the generic skill/workflow router are deferred until their explicit reactivation gates.

### Track E — worktree and branch hygiene

[`agent-worktree-and-branch-hygiene-plan.md`](agent-worktree-and-branch-hygiene-plan.md) combines the two
former Inbox proposals. Phase 1 is dry-run classification plus Git-native bounded retry with no raw recursive
deletion fallback. Phase 2 adopts worktree=session and branch=task with new branches named
`<agent>/<kind>/<topic>`; existing names are grandfathered.

## Inbox disposition — evaluated 2026-07-16

All 14 Inbox documents were evaluated. Actionable work now has one canonical owner in Todo, security- or
evidence-gated work is Deferred, source indexes are archived/superseded, and `docs/1_Inbox/` is empty pending
new captures. Constitution v1.1 records the partitioned Markdown-authority decision.

## Captured strategic input — `4_Reference` (2026-07-14 drop, triaged)

A strategy/research set was dropped into the inbox and triaged: the architectural-discovery proposal was
promoted and completed through Constitution v1.0; the three source reports moved to `4_Reference` (source
material, not buildable plans). They overlap the existing corpus (`memory-seed-market-fit-report.md`, the
next-gen blueprint, `agent-rules.md` Working Principles) more than they add; the useful extracted and
remaining ideas are:

- [`../4_Reference/memory-seed-gitlens-competitor-report.md`](../4_Reference/memory-seed-gitlens-competitor-report.md)
  — GitLens as a competitor/integration target; differentiate on decision/reasoning provenance (not
  Git-history features); "memory beside the commit/PR being viewed" tactics.
- [`../4_Reference/memory-seed-strategic-synthesis-report.md`](../4_Reference/memory-seed-strategic-synthesis-report.md)
  — Memory-Quality as a first-class KPI set and a named layered-maturity ladder (raw activity → … →
  institutional knowledge). The measurable, non-gameable subset is now active as
  [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md).
- [`../4_Reference/memory-seed-rectification-priorities-report.md`](../4_Reference/memory-seed-rectification-priorities-report.md)
  — an entry-type taxonomy (Evidence/Interpretation/Decision/…), content authority, and an
  outcome-comparison benchmark (with/without Memory Seed). Provenance/authority/actionability is now active
  as [`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md);
  the broader entry-type taxonomy and outcome benchmark remain unpromoted. Several of the report's other
  items are already shipped/covered (two-stage capture, retrieval-over-graph, trust/security groundwork).

The GitLens integration tactic, broader entry-type taxonomy, layered-maturity model, and outcome-comparison
benchmark remain reference input rather than active work.

## Doc-lifecycle Phase 2 (housekeeping)

Tracked in [`document-lifecycle-system-plan.md`](document-lifecycle-system-plan.md) (Phase 1 — lanes +
front door — shipped). **The bulk migration shipped 2026-07-17:** all 43 `2_Todo/completed/` docs plus the
nested `agent-templates/` moved to `5_Completed/`, every inbound reference was repaired, and the folder is
retired — so no legacy archive sits beside the lanes any more. Remaining: the `docs index` / `docs check`
CLI. *(The former third item — removing an empty `superpowers/specs/` — is dropped: no such directory
exists in the working tree or in git history.)*

## Parked — needs your judgement / market / accounts (not engineering next-steps)

- [`8_Deferred/memory-trace-commercialisation-and-monetisation-report.md`](../8_Deferred/memory-trace-commercialisation-and-monetisation-report.md)
  — pricing/tiers; needs usage + market validation before any build.
- [`8_Deferred/memory-trace-hosted-product-and-security-architecture.md`](../8_Deferred/memory-trace-hosted-product-and-security-architecture.md)
  — hosted/team tier; needs commercial + billing/auth decisions and a later security review.
- **MCP client validation** — register in a client and confirm the agent calls `memory_search` before
  answering; record client-specific setup. Command: `claude mcp add memory-seed -s user -- uvx --from
  memory-seed memory-seed-mcp --stdio`.
- **Launch assets** — real terminal screenshot/GIF (`init`, mcp-validate, a memory lookup) to replace the
  README S6 placeholders; decide the launch-note audience.
- **Optional semantic extra** — decide whether to add `memory-seed[semantic]` (Model2Vec embeddings);
  keep the default path dependency-light unless it shows clear value.
- **Community feedback** — watch agent-compatibility issues across Codex/Claude/Gemini/Copilot clients.

## Discipline

- **Releases:** never cut/publish without the user's explicit go; the PyPI push is a manual-approval gate.
  Current plan: cut 2.19 after the memory-quality trio lands.
- **Ranking:** keep `main` behavior stable; run ranking experiments on a branch, merge only after **both**
  fixtures **and** the shipped real-corpus A/B (`ranking-ab`) show a clear win with no text-ranking
  regression. This is the enforced "expose before you rank" gate from the trio's item 1.
- **Branches/worktrees: branch = workstream** (policy set 2026-07-15). Batch follow-on fixes/evolutions of
  the *same goal* onto one `claude/<kind>/<topic>` branch — the tell is an `evolves`/`related` edge to the
  entry just written, or the same subsystem — and merge the batch to local `main` at a **stable, tested
  stopping point** (self-gated; no per-merge approval pause). Open a new branch only for a genuinely new
  goal. Writing agents stay in their own `.<agent>/worktrees/` namespace (guard enforced).

## Continuity naming

- **Memory Seed** — core runtime, CLI, MCP, retrieval, validation, session files.
- **Memory Trace** — companion package + human review UI (`pip install "memory-seed[trace]"`, `memory-trace`).
- **Trail** — the Memory Trace view for branch/supersession/evolution.
- **Lense** — legacy compatibility name only. **Explorer** — historical working name only.
