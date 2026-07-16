---
title: "Memory Seed Post-Trail Platform Review Proposal Set"
date: "2026-07-16"
project: "memory-seed"
status: "inbox"
priority: "P2-P3"
next_action: "Complete React Trail parity and B0b acceptance, then review each bounded proposal independently."
related:
  - "docs/2_Todo/memory-trace-next-generation-implementation-roadmap.md"
  - "docs/2_Todo/memory-provenance-and-authority-taxonomy-proposal.md"
  - "docs/2_Todo/memory-quality-metrics-v0-proposal.md"
  - "docs/2_Todo/document-lifecycle-system-plan.md"
---

# Memory Seed Post-Trail Platform Review Proposal Set

Status: **INBOX**. This is a triage record, not approval to implement any item.
Priority: P2/P3 after React Trail parity and B0b acceptance.
Source: An independent repository review supplied on 2026-07-16. It inspected stale `origin/main` at
`332c310`; this triage was rebaselined against local `main` at `cd050c9`, which was ahead of that remote.

## Purpose

Retain the useful platform ideas from the review without reopening work already completed or creating
competing owners for active plans. The first product gate is React Trail parity; these ideas do not displace
that gate.

## Rebaselined disposition

| Review recommendation | Disposition on local `main` | Owner / result |
|---|---|---|
| Renderer selection and B0b evidence are unresolved | Superseded. Cytoscape 3.34.0 is selected and the React graph/workspace adapter is merged; Trail parity and final acceptance remain. | Roadmap Phases 4-5; docs corrected in this batch. |
| Evidence Envelope and Task Packets consume Evidence Packs | Retain as a bounded, referential contract. | [`evidence-envelope-and-task-packet-reference-proposal.md`](evidence-envelope-and-task-packet-reference-proposal.md) |
| Provenance, authority, and actionability platform schema | Already owned by an active constitutional gate. | [`../2_Todo/memory-provenance-and-authority-taxonomy-proposal.md`](../2_Todo/memory-provenance-and-authority-taxonomy-proposal.md) |
| Human review queue, document lifecycle graph, and quality inspection | Retain as a derived, read-only view that depends on existing lifecycle, quality, and provenance work. | [`derived-review-queue-and-document-lineage-proposal.md`](derived-review-queue-and-document-lineage-proposal.md) |
| One provider lifecycle and publishability boundary | Retain as an advisory evaluation, without changing existing provider plans. | [`capability-status-and-publishability-boundary-proposal.md`](capability-status-and-publishability-boundary-proposal.md) |
| Projection modules | Covered by the candidate projection contract and its implementation plan. | [`../3_Spec/draft/derived-read-model-projection-contract.md`](../3_Spec/draft/derived-read-model-projection-contract.md) |
| Quality metrics inspection lens | Already owned by the active read-only metrics proposal. | [`../2_Todo/memory-quality-metrics-v0-proposal.md`](../2_Todo/memory-quality-metrics-v0-proposal.md) |
| Thin VS Code / GitLens surface | Keep as reference input until local APIs and Trail parity are accepted. | [`../4_Reference/memory-seed-gitlens-competitor-report.md`](../4_Reference/memory-seed-gitlens-competitor-report.md) |

## Corrections made while triaging

- The review's claim that the renderer choice was pending was stale; the current docs now record the Cytoscape
  decision and the implemented React graph/workspace behaviour.
- The review's test count was stale; current validation is 140 Memory Trace tests, not 130.
- The draft projection contract now reflects the shipped Phase 1 SQLite projection without promoting the
  remaining G6/G7 and progressive-load guarantees to accepted behaviour.
- The review conflated two performance surfaces. Memory Trace's projected read path is distinct from the
  generic `memory_search` path, so no generic search-performance claim is changed without a new measurement.
- Root README screenshot placeholders are already tracked as a parked launch-assets task; this set creates no
  duplicate visual-assets proposal.

## Proposed sequence

1. Complete React Trail parity and B0b acceptance, including accessibility and scale evidence.
2. Consider the Evidence Envelope reference only if Timeline Evidence Packs and Task Packets need a stable,
   cross-surface hand-off.
3. Consider the derived review queue/document-lineage view after document-lifecycle Phase 2, quality metrics
   v0, and the provenance gate establish authoritative inputs.
4. Consider capability status and publishability only after explicit local security/privacy review.
5. Revisit a thin VS Code surface only when the local read API and Trail semantics are stable.

## Guardrails

- Markdown remains canonical; every queue, status surface, and report is rebuildable derived output.
- No proposal may silently make generated or provider output agent-actionable.
- No proposal adds a universal mutable platform database, remote upload, or automatic document-state change.
- Promotion of one item neither approves nor blocks the others.

## Acceptance criteria for this triage

- Every retained recommendation has a single visible owner or a bounded Inbox proposal.
- Superseded review claims are corrected without downgrading accepted current work.
- The next implementation gate remains React Trail parity rather than a new platform abstraction.
