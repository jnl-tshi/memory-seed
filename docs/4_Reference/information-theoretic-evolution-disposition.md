---
title: Information-theoretic evolution proposal — disposition against shipped capability
status: disposition
date: 2026-07-25
sources:
  - ../7_Replaced/information-theoretic-evolution-exploration.md
  - INBOX-CAPABILITY-CROSSWALK.md
  - ../CONSTITUTION.md
  - ../3_Spec/draft/adr-lifecycle-sidecar-contract.md
  - ../3_Spec/draft/edge-confidence-metadata.md
  - ../3_Spec/draft/link-retraction.md
  - ../3_Spec/lifecycle-edge-linking-sidecars.md
  - ../3_Spec/memory-trace-derived-artifact-provenance-contract.md
  - ../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md
  - ../2_Todo/memory-quality-metrics-v0-proposal.md
  - ../2_Todo/0_NEXT_STEPS.md
---

# Information-theoretic evolution proposal — disposition

## Purpose

The [information-theoretic evolution proposal](../7_Replaced/information-theoretic-evolution-exploration.md)
(received 2026-07-25) frames Memory Seed as a progressive knowledge-refinement pipeline governed by
information-theoretic lenses. This document dispositions it through the same discipline the
[inbox capability crosswalk](INBOX-CAPABILITY-CROSSWALK.md) applied to the fifteen 2026-07-20
explorations: each claim is scored against what the Constitution, live contracts, and shipped code
actually do — not against the proposal's own characterisation of the status quo.

**Disposition, 2026-07-25.** The proposal is retired to `7_Replaced/` on arrival. Most of its
principles are already ratified constitutional law or drafted contract; its territory overlaps
heavily with the retired exploration sets (notably B2 sidecar-lens, B3 deterministic generation,
B5 knowledge lenses, and the A6/B1 constitutional-principle sets) whose surviving residues the
crosswalk already routed into owner plans. Three residues from this proposal survive and are
extracted into owner documents (see [Residues](#residues)). Nothing else is promoted; nothing is
deleted.

`Delta` values follow the crosswalk: **none** (covered by shipped code or a live/ratified layer),
**narrow** (mostly covered; one named gap), **genuine** (materially uncovered and unclaimed).

## Coverage

| Proposal claim | What covers it | Delta |
|---|---|---|
| Provenance for every derived artifact (edges, topics, ADRs, diagrams) | Constitution Invariant #3; `memory-trace-derived-artifact-provenance-contract.md`; the link-swarm validator's quote-grounding requirement; `Memory-Entry:` commit trailers | none |
| Reconstructability — every layer rebuildable from the level beneath | Constitution Invariant #6: every non-Markdown store is a derived, fully rebuildable projection | none |
| Governance — Constitution evolves only by reviewed proposal, never automatically | Constitution §11 Governance, practiced through the v1.1–v1.4 amendment log; the proposal restates the ratified mechanism | none |
| "Structure must earn its existence" / Information Gain as a gate | Constitution §9 five-question test; §3 "Immediate value before future value"; crosswalk row A6-9 (none) | none |
| Information Gain as a **measured metric** | Quality-metrics v0 framework ships the metric scaffolding; the constrained-context gold set (crosswalk genuine delta, A5) is the prerequisite and does not exist | narrow — owner is the quality-metrics plan; blocked on the A5 gold set |
| ADR layer (compressed architectural knowledge above entries) | [ADR lifecycle sidecar contract](../3_Spec/draft/adr-lifecycle-sidecar-contract.md) (draft), gated on the semantic-record plan's walking skeleton; NEXT_STEPS already sequences "prove append-only ADR sidecars on three real decisions" | narrow — the gap is implementation of an owned draft, not architecture |
| Knowledge distillation — ADRs preserve decision-making ability, not summary prose | The draft ADR contract's authority split: sidecar owns lifecycle, entries own narrative rationale and evidence | none (within the draft's scope) |
| Redundancy as independent evidence; losing one edge does not lose the knowledge | Four never-merged edge kinds; supersession damping never removes results (Invariant #7); no single edge is authoritative for retrieval | none |
| Entropy / "does this edge reduce retrieval uncertainty" framing | Lens only — no mechanism proposed; the shipped analogue is "Expose before you rank" + `ranking-ab` ablation, which measures whether a signal helps | none as philosophy; the measurement gap is the same A5 gold set above |
| Channel capacity / MDL / "minimal but sufficient context" | **Not present at any layer** — crosswalk row A6-5 marked this *genuine*, and this proposal independently re-derives it | genuine — extracted as Residue 2 |
| Information Bottleneck — discard context that does not change the answer | Same gap as A6-5; the Evidence Pack records omissions with reasons but no surface enforces sufficiency-minimality | genuine — folded into Residue 2 |
| Deterministic confidence from independent evidence, inspectable breakdown | `edge_confidence` today stores **model-judged** advisory confidence (human-gated, tier-marked); no deterministic evidence score exists | genuine — extracted as Residue 1 |
| Centrality (degree/betweenness/PageRank) driving node prominence | The graph renders typed edges, community colour, confidence fading; no centrality metric is computed anywhere | genuine — extracted as Residue 3 |
| Hierarchical graph layout (ADR gravity wells, Constitution tier above ADRs) | Ratified Phase D1 graph plan (Settled cose default, motion-never-evidence, halo isolates); ADRs do not exist yet as nodes | narrow — declined for now: premature before the ADR layer ships; revisit when ADR nodes exist |
| Topics as a compression layer between entries and ADRs | Topics are a **controlled classification vocabulary** (`.memory-seed/topics.yaml`), not compressed decisions; harmless as a lens, wrong as architecture | narrow — declined: mischaracterises the shipped topic system |
| "Compress aggressively" | Only ever downstream of Invariant #2 — compression happens in derived/ADR layers; entries are never rewritten. The proposal is compatible but silent on this constraint | none, with the constraint stated here |
| Sidecars as extraction/compression/representation lenses | The retired B2 sidecar-lens exploration proposed this taxonomy; the crosswalk found the shipped sidecar contracts already cover it | none — previously dispositioned |

## Tensions corrected at disposition

1. **"Semantic similarity" listed as deterministic evidence is wrong.** Embedding similarity is
   model-dependent (Invariant #5) and not reproducible across model versions. A deterministic
   evidence score may not include it except as an explicitly pinned, non-deterministic-flagged
   input. Residue 1 drops it.
2. **Deterministic confidence vs. the 2026-07-25 `edge_confidence` campaign.** The 696 swarm edges
   carry model-judged confidence — what the proposal's principle 2 forbids. They are advisory,
   human-gated, and constitutionally documented (§4 Policy), so they stand; the reconciliation is
   Residue 1's *derived* deterministic score computed at read time alongside — never replacing —
   the authored advisory value. No retraction campaign is warranted.
3. **The hierarchy diagram overstates topics** (see Coverage). Adopted nowhere.

## Residues

Extracted 2026-07-25 into owner documents; this table is the pointer record.

| # | Residue | Owner document | Shape |
|---|---|---|---|
| 1 | Deterministic evidence score for edges — shared `F:` files, shared topics, explicit in-prose reference, human authorship — computed as a **derived read-time projection** (Invariant #6), inspectable per-component, never stored, never model-derived | [`3_Spec/draft/edge-confidence-metadata.md`](../3_Spec/draft/edge-confidence-metadata.md) §"Deterministic evidence score" | design residue in the owning draft spec |
| 2 | **Minimal but sufficient context** — retrieval provides the smallest context that preserves the ability to decide; closes crosswalk genuine gap A6-5 (+ A6-rule "decision quality under constrained context") | [`CONSTITUTION.md`](../CONSTITUTION.md) §3 | `[candidate]` principle, pending JNL ratification |
| 3 | Centrality-driven node prominence (size/visual weight, not position) as a graph increment, sequenced **after** Phase D1 | [`2_Todo/0_NEXT_STEPS.md`](../2_Todo/0_NEXT_STEPS.md) open item | roadmap follow-up |
