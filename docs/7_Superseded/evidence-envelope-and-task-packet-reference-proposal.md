---
title: "Evidence Envelope and Task Packet Reference Proposal"
date: "2026-07-16"
project: "memory-seed"
status: "superseded"
priority: "P2"
next_action: "After React Trail parity, decide whether a stable cross-surface evidence hand-off is needed; if so, draft fixtures before changing Task Packets."
dependencies:
  - "React Trail parity and B0b acceptance"
  - "docs/5_Completed/worker-context-minimisation-proposal.md"
  - "docs/2_Todo/memory-provenance-and-authority-taxonomy-proposal.md"
related:
  - "docs/2_Todo/memory-trace-ai-timeline-summarisation-plan.md"
  - "docs/2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md"
superseded_by: "../2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md"
superseded_on: "2026-07-16"
---

# Evidence Envelope and Task Packet Reference Proposal

Status: **SUPERSEDED 2026-07-16** by section 11.1 of
[`memory-trace-evidence-annotations-and-projection-architecture.md`](../2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md).
Priority: P2 after React Trail parity and B0b acceptance.
Source: The 2026-07-16 post-Trail platform review triage.

## Problem

Timeline Evidence Packs, graph fixtures, and delegated task packets may need to refer to the same bounded
evidence selection without copying unversioned excerpts or inventing separate provenance fields. Today their
individual contracts are useful, but their cross-surface hand-off is not explicit.

## Proposal

Define a small, versioned, **referential** `EvidenceEnvelope` fixture. It describes a selected evidence set;
it does not become a new canonical evidence store. A minimum envelope should contain:

- `selection` and `corpus_revision`;
- `generated_at` and freshness boundary;
- canonical entry or evidence references, with stable fingerprints where required;
- provenance and authority references, rather than copied authority policy;
- constraints, exclusions, and an explicit unavailable/partial state.

If the fixture proves useful, a Task Packet may later contain an optional `evidence_envelope_ref`. The existing
`persona` and `context_load` fields remain owned by the worker-context proposal and are not duplicated here.

## Non-goals

- No universal evidence mega-schema or mutable envelope database.
- No replacement for Timeline Evidence Packs, graph fixtures, annotation evidence, or Task Packets.
- No provider call, network transport, automatic retrieval, or change to agent startup context.
- No new authority or actionability policy; those remain owned by the provenance taxonomy.

## Dependencies and sequence

React Trail parity is the immediate gate. Any follow-on design must reuse the existing Evidence Pack and
Task Packet contracts, and must take the provenance/authority gate as input. A successful proposal could be
independently promoted after B0b acceptance; it does not wait for the later review-queue proposal.

## Acceptance criteria

- A versioned fixture is sufficient to resolve every referenced canonical record or state it unavailable.
- Compatibility fixtures cover a Timeline Evidence Pack, a renderer-neutral graph fixture, and a Task Packet.
- Rebuilding the fixture from canonical Markdown yields the same references and constraints.
- No new network, write, or actionability path is introduced.
