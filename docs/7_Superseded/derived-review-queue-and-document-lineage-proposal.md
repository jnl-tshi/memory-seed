---
title: "Derived Review Queue and Document Lineage Proposal"
date: "2026-07-16"
project: "memory-seed"
status: "superseded"
priority: "P3"
next_action: "After React Trail parity and the named prerequisite contracts, define deterministic fixtures for a read-only review projection."
dependencies:
  - "React Trail parity and B0b acceptance"
  - "docs/2_Todo/document-lifecycle-system-plan.md"
  - "docs/2_Todo/memory-quality-metrics-v0-proposal.md"
  - "docs/2_Todo/memory-provenance-and-authority-taxonomy-proposal.md"
related:
  - "docs/3_Spec/draft/derived-read-model-projection-contract.md"
  - "docs/2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md"
---

# Derived Review Queue and Document Lineage Proposal

Status: **SUPERSEDED 2026-07-16** by
[`memory-seed-workflow-evidence-and-review-workbench-plan.md`](../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md).
Priority: P3 after React Trail parity, document-lifecycle Phase 2, quality metrics v0, and the provenance gate.
Source: The 2026-07-16 post-Trail platform review triage.

## Problem

Review-relevant signals currently live in separate authoritative sources: lifecycle check findings, proposal
metadata, quality observations, annotation requests, and session/document transition evidence. A human should
be able to inspect the outstanding decisions and their source evidence without treating a dashboard as truth.

## Proposal

Build a deterministic, read-only projection that can present review items and document-to-decision lineage.
A minimum `ReviewItem` shape is:

```text
item_id, kind, source_ref, requested_decision, evidence_refs,
authority_and_freshness, derived_status, resolution_entry_id
```

Document lineage is a derived relation such as `entry -> promoted_document -> document`. It is produced from
canonical links and folder/lifecycle metadata; it does not create a second lifecycle authority.

## Non-goals

- No automatic human judgement, promotion, rejection, or document movement.
- No mutable review-store, inferred semantic edge promoted as fact, or new canonical link grammar.
- No annotation may appear actionable before the provenance/authority gate allows it.
- No hidden unavailable source: absence, staleness, and dangling references must remain visible.

## Dependencies and sequence

The document-lifecycle plan owns `docs index` / `docs check`; quality metrics v0 owns the measurement inputs;
the provenance proposal owns actionability. This proposal joins those outputs only after they have deterministic
fixtures. It should not begin while React Trail parity is the primary B0b acceptance gap.

## Acceptance criteria

- The same Markdown corpus produces the same review items and document-lineage edges.
- Every item links to canonical source evidence and states whether that evidence is unavailable or stale.
- A resolution writes to the existing canonical source path and is then reflected by the projection.
- The projection can be deleted and rebuilt without loss of review or lifecycle truth.
