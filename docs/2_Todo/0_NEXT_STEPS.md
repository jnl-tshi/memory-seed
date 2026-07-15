# Next Steps

Status: **ACTIVE — resumed 2026-07-14, Constitution-aligned** (Constitution v1.0 ratified the same day).
Updated: 2026-07-15

> ▶ **Foundation shipped 2026-07-15 → the memory-quality trio now leads.** The
> [derived-projection Phase 1](derived-projection-implementation-plan.md) (git-watermark warm start +
> atomic swap + three read-path perf refinements) **shipped 2026-07-15** — the plan's former "do first"
> foundation is done. Work still sequences *under* [`docs/CONSTITUTION.md`](../CONSTITUTION.md) **v1.0**
> (each item answers the five-question test — Capture / Validation / Retrieval / Trust / Application — and
> respects Invariant #6: Markdown = source of truth; every DB/cache is a derived, rebuildable projection).
> The current lead is the **Ranking & graph quality** trio (below); the projection's remaining
> incremental-ingest fast-follow is deferred as low-urgency (reads are already ~3.9 ms). **2.19 is cut
> after the trio lands** (JNL decision 2026-07-15). **React (B2) is deferred** — JNL wants the Trace
> **graph view** to get its due attention first (a named pre-React workstream, below).
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
- **Release cadence:** cut **2.19 after the memory-quality trio lands** (JNL decision 2026-07-15) so the
  release carries the retrieval/capture-quality wins too — then hold for the user's go on the PyPI push (no
  unprompted release; the publish is a manual-approval gate).

## Live work — sequenced (Constitution-aligned)

Active work, sequenced under the Constitution (each item answers the five-question test — Capture /
Validation / Retrieval / Trust / Application — and respects Invariant #6). The **foundation shipped
2026-07-15**, so the **Ranking & graph quality** trio now leads; the feature tracks follow.

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

### Ranking & graph quality ← CURRENT LEAD — promoted from inbox 2026-07-14 (sequence: gate → surface → capture)

The memory-quality trio from the 2026-07-13 freshness-ranking session, **approved and promoted from the
inbox 2026-07-14**; **it now leads** (the foundation shipped 2026-07-15). These *are* the product getting
better (each answers the five-question test), so they sit above the Track A tails. Build in this order —
the gate first, because the successor boost depends on it:

1. **`ranking-ab` + the "expose before you rank" amendment** —
   [`real-corpus-ranking-validation-gate-proposal.md`](real-corpus-ranking-validation-gate-proposal.md).
   A reusable `memory-seed ranking-ab` command + a graph-edge-contract rule requiring a real-corpus A/B
   (not just green fixtures) before any default ranking flip. Five-question → **Validation + Trust**.
   *Gates item 2's ranking half.*
2. **`superseding_head` (+ gated replacement boost)** —
   [`supersession-successor-surfacing-proposal.md`](supersession-successor-surfacing-proposal.md).
   Closes the supersedes/evolves asymmetry: `supersedes` only *damps* the retired entry while `evolves`
   *surfaces* its successor via the shipped `evolved_head`. Step 1 (`superseding_head`, additive/read-only)
   can ship now; step 2 (bounded boost) waits on item 1's A/B gate. Five-question → **Retrieval + Trust**.
3. **`link audit --apply` sidecar scaffold** —
   [`lifecycle-link-authoring-assist-proposal.md`](lifecycle-link-authoring-assist-proposal.md).
   Scaffolds inert `classify_pending` sidecar stubs (never auto-classifies — author judgment stays,
   append-only) so lifecycle edges stop getting dropped at session end — which matters more now that
   supersession damping is on by default (a dropped edge is invisible to ranking). Five-question →
   **Capture**.

### Track A — close the open tails (small, finish-what-shipped)

1. **`integration_mode` Phases 2–4** — [`configurable-integration-mode-plan.md`](configurable-integration-mode-plan.md).
   P0.1 (setting + reader + `esr` surfacing) shipped; remaining: the agent contract reads/obeys the mode
   (skills/agent-rules), PR/`session integrate` tooling, and a bootstrap heuristic. *Unblocks OpenSSF.*
2. **`topics suggest --from <file>`** — [`memory-trace-topic-neighbourhoods-plan.md`](memory-trace-topic-neighbourhoods-plan.md).
   The single named item left before that plan is fully done (Phases 0–4 shipped).
3. **Evolution-edges continuity display in Trail** — [`evolution-edges-plan.md`](evolution-edges-plan.md).
   P1 + lineage-seeding shipped (2.18.0); the last sub-item of the Trace lineage pass — render
   `continuity:` chains as a Trail display axis — is unbuilt.
4. **Related-entries P2** — [`related-entries-p2-mutation-plan.md`](related-entries-p2-mutation-plan.md).
   Approved 2026-07-05, unbuilt: controlled `link add` (current-entry) + explicit historical backfill.
   Sequence after 1–3; it's a convenience increment, not a blocker.
5. **Session decision diagrams Phase 3** — [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md).
   Phases 1–2b shipped (sidecars, validation, reader + Trail/Graph badge & zoom viewer). Phase 3
   (exportable report / handover pack) is sizable and **gated on a product greenlight**.
6. **OpenSSF credibility** — [`openssf-credibility-proposals.md`](openssf-credibility-proposals.md).
   `SECURITY.md`, a CI gate, G0–G2. Approved-not-built and **blocked on integration-mode Phases 2–3**.

### Track B — Memory Trace next generation (the promoted direction, 2026-07-11)

Governance (read to sequence, not build): [`memory-trace-product-and-system-architecture-blueprint.md`](memory-trace-product-and-system-architecture-blueprint.md)
(entry point) → [`memory-trace-next-generation-implementation-roadmap.md`](memory-trace-next-generation-implementation-roadmap.md)
(Phase 0–10 spine; Phases 0–1 delivered) → [`memory-trace-next-generation-coverage-matrix.md`](memory-trace-next-generation-coverage-matrix.md).

- **B1 — Evidence Pack Builder** *(startable now, small, backend-only)* —
  [`memory-trace-ai-timeline-summarisation-plan.md`](memory-trace-ai-timeline-summarisation-plan.md) Phase 1.
  `build_timeline_evidence_pack()`: deterministic JSON over the already-delivered retrieval/graph readers,
  snapshot-tested, **no write path, no provider**. Owns the near-term "Evidence Pack" implementation; the
  canonical shape is the spec [`../3_Spec/memory-trace-derived-artifact-provenance-contract.md`](../3_Spec/memory-trace-derived-artifact-provenance-contract.md)
  (blueprint §4.5 and the evidence-annotations doc are forward supersets — do not build a second builder).
- **B0 — Graph-view attention** *(pre-React; JNL-endorsed 2026-07-15)* — the reason React is deferred:
  JNL wants the Memory Trace **graph view** to get its due attention before any React rebuild. Sits after
  the trio and **before B2**. "The attention it needs" is deliberately underspecified — this workstream
  **opens with a taste-elicitation from JNL** (what's wrong / what they want from the graph), not a guess.
  Vanilla `/api/graph` + `app.js` graph rendering.
- **B2 — React/Vite shell** *(the strategic bet — DEFERRED 2026-07-15; graph-view attention (B0) comes
  first)* —
  [`memory-trace-frontend-architecture-and-design-system-proposal.md`](memory-trace-frontend-architecture-and-design-system-proposal.md)
  (roadmap Phase 2). First increment before any component work: stand up the Vite/TS workspace whose
  **built** assets serve from the wheel with **zero Node at runtime** — proving the packaging spine.
  Gated by the `3_Spec` parity fixtures + vanilla fallback. The current vanilla `/api/*` + `app.js` Trail
  stays the shipped UI until parity is proven.
- **B3 — Evidence annotations & projection** *(long-horizon, after B2)* —
  [`memory-trace-evidence-annotations-and-projection-architecture.md`](memory-trace-evidence-annotations-and-projection-architecture.md).
  Anchors, append-only annotations, SQLite projection — needs the React shell **and** a participant/role
  model first.

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
other. Both sit **below Track A's blocking tails** in priority — small, sequence-flexible guidance changes.

## Captured proposals — awaiting your approval (`1_Inbox/`)

The **memory-quality trio** (supersession-successor-surfacing, real-corpus-ranking-validation-gate,
lifecycle-link-authoring-assist) was **promoted to `2_Todo` 2026-07-14** — see the *Ranking & graph
quality* track above. The **grounding-provenance → write-time links** proposal was **approved and shipped
the same day** — the `consulted` axis on `memory_link_suggest`/`suggest_related_entries` + the
`history_retrieval`/`session_logging` guidance that connects the retrieval and link-authoring loops (layer 3
auto-capture deferred as optional) → [`5_Completed/`](../5_Completed/grounding-provenance-write-time-links-proposal.md).

What remains is the **agent/worktree hygiene** pair: real friction, but developer ergonomics (touches none
of the five questions), so lower priority. Each a verified genuine gap:

- [`worktree-gc-proposal.md`](../1_Inbox/worktree-gc-proposal.md) — a `worktree gc` command with
  lock-aware retry (the namespace guard shipped; removal/GC did not; fixes the recurring OneDrive-lock
  pain). P3. The *executor* the lifecycle proposal below drives — promote it first.
- [`agent-namespaced-branch-worktree-lifecycle-proposal.md`](../1_Inbox/agent-namespaced-branch-worktree-lifecycle-proposal.md)
  — worktree=session / branch=task naming + two decoupled lifecycles + post-merge hygiene. **Needs a
  decision from you** (slash vs. hyphen branch naming) and sign-off to edit `agent_collaboration.md` (a
  locked control-plane file); depends on `worktree gc`.

*(The architectural-discovery proposal was approved and promoted to `2_Todo/` — it is the active
Constitution-first work; see the pause banner above.)*

## Captured strategic input — `4_Reference` (2026-07-14 drop, triaged)

A strategy/research set was dropped into the inbox and triaged: the actionable proposal above stayed in
`1_Inbox`; the three source reports moved to `4_Reference` (source material, not buildable plans). They
overlap the existing corpus (`memory-seed-market-fit-report.md`, the next-gen blueprint, `agent-rules.md`
Working Principles) more than they add — the **genuinely net-new** ideas worth mining into proposals:

- [`../4_Reference/memory-seed-gitlens-competitor-report.md`](../4_Reference/memory-seed-gitlens-competitor-report.md)
  — GitLens as a competitor/integration target; differentiate on decision/reasoning provenance (not
  Git-history features); "memory beside the commit/PR being viewed" tactics.
- [`../4_Reference/memory-seed-strategic-synthesis-report.md`](../4_Reference/memory-seed-strategic-synthesis-report.md)
  — Memory-Quality as a first-class KPI set (stale-rate, orphan-rate, evidence/decision coverage) and a
  named layered-maturity ladder (raw activity → … → institutional knowledge).
- [`../4_Reference/memory-seed-rectification-priorities-report.md`](../4_Reference/memory-seed-rectification-priorities-report.md)
  — an entry-type taxonomy (Evidence/Interpretation/Decision/…), a content-trust-level taxonomy, and an
  outcome-comparison benchmark (with/without Memory Seed). Several of its 10 items are already
  shipped/covered (two-stage capture, retrieval-over-graph, trust/security groundwork).

None are promoted to active work — tell me which net-new items to split into `1_Inbox` proposals.

## Doc-lifecycle Phase 2 (housekeeping)

Tracked in [`document-lifecycle-system-plan.md`](document-lifecycle-system-plan.md) (Phase 1 — lanes +
front door — shipped): the `docs index` / `docs check` CLI, bulk-migrating the 43 `2_Todo/completed/`
docs into `5_Completed/`, and removing the empty `superpowers/specs/`.

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
  fixtures **and** a real-corpus A/B (`ranking-ab`, once built) show a clear win with no text-ranking
  regression. This is the "expose before you rank" gate the trio's item 1 hardens.
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
