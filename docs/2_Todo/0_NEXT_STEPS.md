# Next Steps

Status: **ACTIVE — Constitution-aligned** (v1.0 ratified 2026-07-14; v1.1 2026-07-16; v1.2 2026-07-17;
v1.3 2026-07-19).
Updated: 2026-07-20

> ▶ **Foundation and memory-quality core shipped 2026-07-15.** The
> [derived-projection Phase 1](derived-projection-implementation-plan.md) (git-watermark warm start +
> atomic swap + three read-path perf refinements) **shipped 2026-07-15** — the plan's former "do first"
> foundation is done. Work still sequences *under* [`docs/CONSTITUTION.md`](../CONSTITUTION.md) **v1.3**
> (each item answers the five-question test — Capture / Validation / Retrieval / Trust / Application — and
> respects Invariant #6: Markdown = source of truth; every DB/cache is a derived, rebuildable projection).
> **v1.3 (2026-07-19)** amended Invariant #2 with write-surface parity: any surface that writes session
> memory must run the same validation as every other, which is what permitted — and constrains — the
> gated MCP write path below.
> The ranking/graph core now includes the full-corpus gate, `superseding_head` plus its bounded boost,
> and inert `link audit --apply` scaffolding. **2.19.0 released 2026-07-17** (live on PyPI). **B0a
> graph/workspace contracts and renderer evidence are complete;
> B2/B0b React parity is the current lead.** The projection's
> incremental-ingest fast-follow remains deferred as low-urgency (reads are already ~3.9 ms).
Source: the `docs/` lifecycle lanes (folder = state — see [`../README.md`](../README.md)), `CHANGELOG.md`,
and `docs/3_Spec/`. Rebuilt 2026-07-14 from a full inbox+todo evaluation; re-baselined 2026-07-15 after the
Foundation shipped (per-doc status verified against CHANGELOG + code, not this file's prior claims).

## Current state

- **Released: v2.19.0 (2026-07-17)** — live on PyPI, both wheel + sdist; see `CHANGELOG.md`
  "## 2.19.0" for the authoritative list (highlights: memory-quality report/baseline; `link add`;
  `worktree classify --apply`; `docs check`/`docs index`; unified entry grammar + decision-density
  advisory; the breaking `/api/v1` `authority_class` enum rename; OpenSSF hardening — SHA-pinned
  actions, CodeQL, Scorecard, SECURITY/CONTRIBUTING; plus the full 2.18→2.19 tranche folded in).
  The `memory-seed[lense]` deprecated alias **shipped intact in 2.19** (removal never consented) — the
  deprecation-window decision stays open.
- **Foundation SHIPPED 2026-07-15:** derived-projection Phase 1 — git-watermark warm start (O(changes)
  freshness, no whole-corpus scan; ~6.2 s rebuild → ~78 ms warm) + atomic build/swap + schema version, plus
  three read-path perf refinements (freshness memoize, chunk memoize, sidecar-first-class freshness):
  `chunk()` 132 ms → 3.9 ms. Only the **incremental-ingest** fast-follow remains, deferred as low-urgency.
- **Doc lifecycle:** the folder a doc sits in *is* its state. This refresh moved the terminal docs into
  `5_Completed/` / `7_Superseded/` / `8_Deferred/`; only docs with live work remain in `2_Todo/`.
- **Wave 1 + closeout SHIPPED 2026-07-15:** `topics suggest --from`, deterministic timeline Evidence
  Packs, the Trail continuity axis, `superseding_head` plus the gated boost, all four configurable
  integration-mode phases, and lifecycle-link scaffold steps 1–3.
- **Release cadence:** 2.19.0 is **released** (2026-07-17). The next tranche accumulates under
  `CHANGELOG.md` "## Unreleased"; publishing remains a manual-approval gate at the pypi environment.

## Shipped 2026-07-18/19 — unreleased, on local main

None of this was on the roadmap when it was written; it is recorded here so the next sprint starts from
what is true rather than reconstructing it. All of it sits on local main, unpushed.

- **Gated MCP write surface + Constitution v1.3.** `memory_session_append` is now the only way to author
  an entry over MCP, inheriting all nine write-time guards, and `memory_session_integrate` wraps branch
  integration. Both **replaced and removed** `memory_entry_id` and `memory_session_target` — an id plus a
  target path was the entire bypass, and it was the path agents actually used. `dry_run` on both the tool
  and `session append` runs every guard and returns `rendered`: the byte-exact block a real write would
  append. A follow-up pinned the contract that a dry run's `timestamp` is echoed into the real call, so a
  preview at `:59` and a write at `:01` cannot silently mint a different id. Constitution **v1.3** amended
  Invariant #2 with write-surface parity — the amendment is what binds future agents, since the invariant
  never forbade the change.
- **Session-memory integrity.** New `malformed-entry-yaml` links-check error for an unclosed entry
  metadata fence — the signature a bad three-way merge leaves. It was verified by replay against the
  actual corruption: it flags exactly the damaged entry at `ae90e91` and is silent on the repaired file.
  `.gitattributes` now applies `-merge` to `.memory-seed/sessions/**` so git cannot line-merge session
  files at all; concurrent edits conflict wholesale and the structural merge is the only way through.
- **Topic vocabulary 21 → 23** — `security` and `performance` added rather than rewriting the published
  entries that already used them. The vocabulary describes the corpus; it does not constrain it
  retroactively.
- **Trail UI tranche (merged).** Deterministic hand-drawn Trail geometry, middle-third scroll discipline,
  the floating find bar, DRAFT initials rendered as words with file pills, pressure ribbons across the
  whole rail, a tabbed settings menu, collapsible entry metadata, and the full-text/find-bar consolidation
  that removed the competing results dropdown.

### Unscoped discoveries — found by doing the work

Four defects that no one reported and no plan predicted. They are recorded because the pattern matters
more than the individual fixes: each was found by measuring or testing rather than by reading code.

1. **A dark-mode contrast bug the report did not name.** The reported symptom was unreadable pressed-button
   lettering; the same rule was also near-invisible in light mode (cream on cream, 1.15:1).
2. **A self-inflicted capability regression.** Making Enter cycle local matches left the server's full-text
   search — the only thing that reads entry *bodies* — reachable only when the Trail had no local match.
   Flagged when introduced, repaired the same day.
3. **The DRAFT body lint was blind to any entry quoting code.** `_walk_entry_bodies` split the body on
   `fences[1]`, but the metadata opener is ` ```yaml ` and never equals a bare ` ``` `, so `fences[1]` was
   really a body code fence and everything above it was discarded. Found while fixing fence integrity;
   un-blinding it exposed one real violation in a published entry.
4. **82% of search results were filler.** `rank_memory_chunks` never drops zero-score chunks, so an
   entry-granularity search returns the whole corpus ranked. A dropdown hid it; cycling would have marched
   through 82 unrelated entries of a 100-result page with the counter reporting progress.

### Fixed 2026-07-20 — link sidecars were silently lost by `session merge-branch`

Branch-side edits to `.memory-seed/sessions/links/**` used to be discarded without an error.
`_changed_session_paths` diffs *all* of `.memory-seed/sessions`, so the reset loop restored sidecars to
base content — but the fuse had no classifier for `links/` paths, so it never re-imported them. The
`-merge` guard changed the failure's shape rather than causing it: a both-sides edit conflicted and was
misclassified as a *non-session* conflict, aborting the merge loudly; the one-sided case — the common
one — lost silently.

Fixed by making link sidecars a third recognized kind in the fuse, mirroring diagram sidecars exactly
(classification, ref extraction, chronological write, plan/apply wiring, CLI/MCP output). A shared
`_is_recognized_session_tree_path` helper now backs both the conflict classifier and a new
defense-in-depth guard: a branch-touched session-tree path the fuse doesn't recognize is refused with an
issue rather than silently reset, so the next unrecognized sidecar kind fails loudly instead of repeating
this bug. Five regression tests cover the one-sided loss, the two-sided conflict, refusal of an
in-place-modified (stub → live) sidecar block on a branch, and the new guard, all proven through
`session_merge_branch` end to end, not just the fuse in isolation. The trunk-only workaround for
*modifying* an existing sidecar block still holds — that's the append-only invariant, not a merge-tool
gap — and is documented precisely in `agent_collaboration.md`.

## Open decisions — ready for your call

Engineering gates that autonomous work has pushed as far as it reasonably can; each needs one decision
before its next step. (Market/account items live under "Parked" below.)

1. **BG1 steps 5–7 — actionability policy + §7 graduation.** Step 4 (display authority/provenance in the
   inspector) **shipped 2026-07-17**. Step 5–6 add an
   `actionability` field computed by policy with machine-readable reason codes, plus fixtures proving
   generated/provider content **cannot** become actionable on its own; step 7 is the Constitution §7
   amendment that would let annotation/generated content become agent-actionable.
   *Options:* **(a)** build 5–6 now as additive/advisory — everything stays non-actionable in effect,
   fail-closed by construction *(recommended: keeps momentum, adds no trust the model doesn't already
   grant)*; **(b)** hold 5–6 until the participant/role model (B3/Phase 6) exists. Step 7 needs your
   explicit amendment approval regardless of (a)/(b).
2. **Track C.2 — ESR Persona Usage Check.** Flag active personas with no recorded `agent_name` use over a
   conservative window. *Options:* **(a)** propose-and-wait — flag and you approve each deactivation
   *(recommended: consistent with append-only + the live-consent rule; deactivate ≠ delete)*; **(b)**
   automatic deactivation. Resolve before build.
3. **Track A.4 — `memory-seed[lense]` deprecation window.** The deprecated alias + `lense` shim shipped
   intact 2.16→2.19. *Options:* **(a)** announce **2.20** as the drop and remove the alias/shim now the
   window has elapsed *(recommended)*; **(b)** keep one more window. It is a published install path, so
   the call is yours.
4. **Track A.2 — Session decision diagrams Phase 3** (exportable report / handover pack) — sizable, needs
   a product greenlight. *Recommendation:* hold until a concrete handover-pack need surfaces (no current
   pull).
5. **OpenSSF remainder — your GitHub clicks** (only you can do these): enable private vulnerability
   reporting; add branch protection + set `integration_mode: pr` (G2); submit to bestpractices.dev
   (answers drafted on request); confirm PyPI attestations at the next cut.

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
`incremental == full-rebuild` equivalence test. Reads are already ~3.9 ms, and the 2026-07-18
worktree-switch profiling re-confirmed the deferral: chunk parsing is ~0.35s of a ~10.3s rebuild (~3%) at
~500 entries — the dominant 92% (per-merge `git merge-base` spawns) was fixed instead via the process-wide
fork-point memo + `ensure_current` warm starts. Incremental ingest waits until corpus scale
makes parse time material (~5k+ entries). **Phase 2** (git-rooted historical integrity, G6/G7) is the next projection increment after the
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

1. **Related-entries P2** — ✅ **RESOLVED 2026-07-17**.
   [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md). `memory-seed link add`
   ships (newest-entry only: forward-only, idempotent, YAML-only, `links check`-gated). The historical
   backfill is **permitted but deliberately not a command** — Constitution **v1.2** amended Invariant #2
   with a one-off, per-edge-approved, metadata-only exception, which a standing command would violate by
   definition. The sanctioned hand procedure is in the plan; prefer the evolution-edges seeding pass,
   which adds edges to history by writing *new* entries and rewrites nothing.
2. **Session decision diagrams Phase 3** — [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md).
   Phases 1–2b shipped (sidecars, validation, reader + Trail/Graph badge & zoom viewer). Phase 3
   (exportable report / handover pack) is sizable and **gated on a product greenlight**.
3. **OpenSSF credibility** — **in-repo slice SHIPPED 2026-07-17** (greenlit by JNL after the
   implementation-plan checkpoint). [`openssf-credibility-proposals.md`](openssf-credibility-proposals.md).
   Landed: `SECURITY.md` (G0), `CONTRIBUTING.md`, CodeQL + Scorecard workflows, README badges, and both
   workflows hardened (every action SHA-pinned from upstream; least-privilege tokens; OIDC preserved).
   G1 CI was already delivered by codex's `verify.yml`. Expected-score notes:
   [`../4_Reference/openssf-scorecard-notes.md`](../4_Reference/openssf-scorecard-notes.md).
   **Remaining is yours:** enable private vulnerability reporting, branch protection + `integration_mode:
   pr` (G2), the bestpractices.dev submission (answers drafted on request), and attestation confirmation
   at the next release cut.
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
  three-region shell has independent navigation and persisted Inspector dock state.
  **Trail/search parity is substantially closed as of 2026-07-19**: local title/branch/id find-bar cycling
  with eased Trail scrolling, server full-text search reachable from the same bar, one counter and one
  pair of chevrons serving both modes, and the reader easing to the matched section as results are
  stepped. Genuine hits are separated from the ranker's score-0 filler client-side, so the counter reports
  matches rather than corpus size. **Storybook, the formal Playwright harness, and accessibility
  acceptance remain open.** The current vanilla `/` UI remains the supported fallback until explicit
  parity sign-off.
- **B0b — Native graph/workspace implementation** *(started 2026-07-16; implemented through roadmap
  Phases 3 and 5)* — the first React shell provides a lazy Cytoscape graph, bounded initial graph range,
  shared entry selection, right/bottom/auto/hidden persisted Inspector controls, and the additive
  `/api/v1/graph/projection` renderer-neutral contract. The React route now also has exact `mse_` and
  legacy `ms-` entry-ID navigation, ranked search results feeding shared Inspector selection, a recent
  seven-day default graph range with an explicit all-dates control, overview/local/topic filters, typed
  curved edges, selected-context `evolves` routes, focus/minimal/all label policy, keyboard fit/zoom/node
  cycling, and a complete-list alternative. Failed graph refreshes preserve the current view; graph mode
  renders connected context while the list retains unlinked records. **The Inspector reader shipped
  2026-07-17** — a markdown-rendered entry body (frontmatter code block, headings, bullets, inline
  code/bold), search-match subsection highlighting at parity with the vanilla reader, an evidence strip
  (commit + `path:line`), and navigable linked-memories/related-activity cards. **The Trail view shipped
  2026-07-18** (first slice) — a `Trail` presentation mode over `/api/v1/trail` with a pure, testable
  `trailModel` (day-grouped newest-first rows, greedy branch-lane interval packing with the main-lane-0
  guard, commit-time `interpRow`), rendering the git-graph rail (lane segments, solid+phantom main spine,
  rounded-elbow fork/merge connectors, clickable trunk merge dots), row-click selection into the shared
  Inspector, and client-side windowing (Load older). Verified by model invariants on live 458-entry data
  (main alone in lane 0; per-lane disjoint; sane laneCount) via the `window.memoryTraceNextDebug` parity
  harness. **Slice 4a shipped 2026-07-18** — lifecycle-edge arrows: `supersedes`/`evolves`/`related` edges
  route through the reserved relationship zone as dashed arrows with pair precedence (replaces > evolves >
  related), soft/pastel variants, and an adjacent-`supersedes` bow; `supersedes` always shows, `evolves`
  and `related` draw for the selected entry. **Slice 5a shipped 2026-07-18** — a relationship legend
  (replaces/evolves/related dashed keys) and search-as-a-function-over-the-Trail: a client-side substring
  filter over the visible window (title/branch/entry-id) dims non-matching rows and dots, marks matches
  with a dot, and shows a live match count. **Slices 4b + 5b + diagram badges shipped 2026-07-18 —
  the Trail is at full parity with the vanilla feature set**: the two-rule related model (same-branch
  related as chain-primary/secondary row brackets, adjacent same-lane evolves as chain brackets,
  commit-sibling right-edge brackets), two-stage muted/pinned selection, continuity lanes
  (rename/migration/removal glyphs in their own band), and `has_diagram` diamond badges (the field the
  service always computed is now declared on the v1 `GraphNode` — additive contract change, fixtures
  regenerated). The left pane is now a **selection context panel** (typed lifecycle links + commit
  siblings + similar entries; recent entries when nothing is selected), replacing the placeholder
  graph-slice list. Other B0b remainders: file/evolution modes, evidence-backed topology communities and optional
  mild temporal layout, React diagram rendering (the bespoke Arc-2d renderer — a ~250-line port), and
  formal accessibility/scale acceptance.
  Keep the SVG renderer until explicit parity sign-off.
  Only after B0b acceptance may the
  [`structural-provider proposal`](memory-trace-structural-graph-enrichment-provider-proposal.md) define a
  provider-neutral contract and pilot optional `code-review-graph`; providers never own canonical decision
  semantics or alter ranking without exposure and real-corpus validation.
- **BG1 — Provenance and authority taxonomy** *(constitutional gate before actionable annotations or
  agent-influencing generated output)* —
  [`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md).
  Keep provenance, authority, lifecycle, and actionability as separate fields; do not create a single
  trust score. **Steps 1–4 SHIPPED** — the enum-constrained `AuthorityClass`/`ProvenanceClass` on the
  node (2.19), and the inspector now displays authority + provenance distinctly (2026-07-17). Steps 5–7
  (actionability policy, fail-closed fixtures, §7 graduation) are the **open-decisions gate #1** above.
- **BG2 — Memory-quality metrics v0** — ✅ **v0 SHIPPED 2026-07-17; usefulness review COMPLETE**
  (proposal step 6). [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md).
  `memory-seed quality report [--json]`; first baseline at
  [`../4_Reference/memory-quality-v0-baseline.md`](../4_Reference/memory-quality-v0-baseline.md)
  (unlinked 95/431 = 22.0%; DRAFT reason coverage 403/403; BG1-dependent metrics honestly `unavailable`).
  **Review (JNL, 2026-07-17):** the baseline is useful as-is — keep it, set **no** targets. BG2 is done;
  the BG1-dependent metrics stay `unavailable` until BG1 lands (see the open-decisions gate for BG1).
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

1. **Worker Context Contract** — ✅ **SHIPPED 2026-07-17** under live user consent (locked-file edit).
   [`../5_Completed/worker-context-minimisation-proposal.md`](../5_Completed/worker-context-minimisation-proposal.md).
   A packeted worker loads only its Task Packet + at most one domain persona + objective-triggered skills
   (`persona:` + `context_load:` packet fields), skipping load-all-personas / full-index / newest-session
   read while **still** running `base_sha`/preflight/worktree-guard. Lives in `agent_collaboration.md`;
   `agent-rules.md` carries one clause (its 260-line startup budget is now exactly full).
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
former Inbox proposals. **Phase 1 COMPLETE 2026-07-17**: `memory-seed worktree classify` (dry-run,
evidence per verdict, fails closed) and `--apply` (destructive; shipped under live consent; reclassifies at
apply time, git-native with bounded retry, no raw deletion, branches untouched). Phase 2 — lifecycle
guidance adopting worktree=session and branch=task with `<agent>/<kind>/<topic>` names — remains; existing
names are grandfathered.

## Inbox disposition — evaluated 2026-07-16, re-triaged 2026-07-20

The 2026-07-16 pass evaluated all 14 Inbox documents: actionable work got one canonical owner in Todo,
security- or evidence-gated work went to Deferred, source indexes were archived or superseded.
Constitution v1.1 records the partitioned Markdown-authority decision.

A new drop arrived 2026-07-18 (two 7-document proposal sets, a product proposal, and a design-reference
folder) and was assessed but deliberately not promoted — see
[`INBOX-ASSESSMENT.md`](../1_Inbox/INBOX-ASSESSMENT.md). Triaged 2026-07-20:

- **Living Archive / Editorial Focus product proposal → `2_Todo`; §14 answered the same day.**
  [The proposal](memory-trace-living-archive-and-editorial-focus-proposal.md) was the most mature document
  in the drop. Promoted so it is visible on the roadmap rather than buried, then partly unblocked: **the
  Community Decision Brief slice is approved to build** — deterministic, ephemeral, no provider — because
  its fields already exist as DRAFT labels and graph edges, so it needs no new capture. Briefs are
  ephemeral by default and exportable only on request, keeping generated output out of the corpus per
  Invariant #6. Adoption as the B0b visual target is gated on a task-completion test recorded inside
  [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md), since nothing today
  measures whether a grounded decision was actually reached. **Still deferred by choice:** the Pro/BYOK
  boundary (§14.3), because that *is* the commercialisation question and this proposal cites the deferred
  report as a source; and both naming questions, until a first brief exists to name. Sections 5 and 9 stay
  parked; `8_Deferred/` is untouched.
- **Both proposal sets (14 documents) → `7_Superseded`, retired 2026-07-20.** Step 1 of the assessment's
  corrected sequence ran first as
  [a current-capability crosswalk](../1_Inbox/INBOX-CAPABILITY-CROSSWALK.md): 82 claims scored against the
  owner documents and shipped code rather than the proposals' own account of the status quo. Most were
  already constitutional law or already-shipped capability the proposals understated — the Evidence Pack,
  typed `supersedes`/`evolves`, blended retrieval — and five conflicted with explicit owner non-goals.
  A6 and B1 turned out to be the same document written twice. The sets were then de-numbered, renamed
  `-exploration`, and retired pointing back at the crosswalk, which is now the more accurate record.
  **Nothing was deleted and nothing was promoted.**

  The ten claimed deltas were **adversarially re-verified before retirement** — a pass told to falsify
  each rather than confirm it. Five survived clean; five were true only under a narrow reading and were
  reworded; **one was outright false** (the crosswalk asserted evidence-proportional-to-consequence was
  absent from every constitutional layer, missing a *cited* §3 principle at `CONSTITUTION.md:105-106`).
  The crosswalk was corrected before it became the supersession target.

  **Where the surviving residues went:** the constrained-context decision-quality benchmark into
  [memory-quality-metrics-v0-proposal.md](memory-quality-metrics-v0-proposal.md); record-level queryable
  absence into [the semantic-record plan](memory-seed-semantic-record-and-signal-foundation-plan.md)
  Phase 1, which also now discharges step 2 of the sequence — it already models three decisions against
  the ADR contract, so only the ambiguity-vs-cost measurement was added. Open-question and assumption
  lenses gained an owner on the same day when
  [the Living Archive proposal](memory-trace-living-archive-and-editorial-focus-proposal.md) was promoted.

  **Still ownerless — three candidates, recorded so they are not lost:**
  1. **Decision-change impact report** — propagating a decision change to the plans, specs and tasks it
     affects. `link audit` detects uncaptured structural neighbours only. Large and genuinely unowned;
     the assessment's scope-multiplication warning applies directly, so this is a candidate, not a queue
     item.
  2. **Cross-provider output conformance suite** — Invariant #5 makes model independence law, and nothing
     tests it: no fixture corpus, no threshold. Downstream of an extraction pipeline that does not exist.
  3. **Declared entry `intent` field** — genuinely uncovered (no such field; stage is inferred from
     prose), but its *value* is contested. Do not make it mandatory without evidence it beats existing
     topics, DRAFT sections, branch and `F:` evidence.

  **Steps 3–5 remain undone** and no longer gate anything: step 3's gold set is the benchmark above,
  step 4 pilots the open-questions lens under its new owner, step 5 decides promotions. The inbox is
  clear regardless — that is the stop rule.
- **Raw design captures → `4_Reference/archived`.** Seven mood-board screenshots were archived once their
  palette and hierarchy themes had been extracted into the folder README; the five generated mockups stay
  in `1_Inbox` because live documents cite them.

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
retired — so no legacy archive sits beside the lanes any more. **`docs check` SHIPPED 2026-07-17** (0
errors / 29 warnings on the live tree; its first run caught three real `spec_binding` defects). Remaining:
`docs index`, secondary-YAML backfill, and P3 (wire `docs check` into `esr` + CI). *(The former third item — removing an empty `superpowers/specs/` — is dropped: no such directory
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
  2.19.0 released 2026-07-17; the next tranche accumulates under `CHANGELOG.md` "## Unreleased".
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
