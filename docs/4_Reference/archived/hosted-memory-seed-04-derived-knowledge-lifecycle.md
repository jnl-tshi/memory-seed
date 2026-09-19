---
title: "Archived source — 04-derived-knowledge-lifecycle"
source_path: "docs/1_Inbox/memory-seed-hosted-proposals/04-derived-knowledge-lifecycle.md"
captured_on: "2026-09-18"
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
archive_note: "Copied from the primary checkout without deleting or modifying the untracked original; superseded assumptions are preserved as source evidence."
---

# Proposal 4 — Derived Knowledge Lifecycle

## Objective

Separate authored Memory Seed knowledge from model-derived knowledge so that the system can improve its interpretation over time without rewriting historical truth.

---

## Authored Knowledge

Examples:

- DRAFT decisions
- ADRs
- Constitution
- explicit user comments
- authored evidence
- explicit human decisions

These should remain stable historical records.

---

## Derived Knowledge

Examples:

- inferred graph edges
- inferred topic membership
- similarity scores
- duplicate likelihood
- ADR relevance probability
- constitutional relevance probability
- curator confidence
- graph-strength metrics

These should be rebuildable.

---

## Proposed Storage Separation

```text
Authored / canonical
--------------------
conversation_events
decisions
decision_versions
adrs
constitution_versions
explicit_evidence

Derived
-------
derived_edges
derived_topics
derived_scores
curator_runs
curator_predictions
candidate_links
```

---

## Why This Matters

Suppose a later benchmark shows:

```text
OpenRouter model edge precision: 91%
Jev edge precision:              97%
```

Memory Seed should be able to rebuild the derived layer:

```text
rebuild-derived-state --provider jev-v2
```

without changing the original decisions or conversations.

---

## Provenance Requirements

Every derived record should identify:

- source records
- provider/model
- prompt/schema version
- timestamp
- confidence
- candidate-generation method
- evidence packet
- whether it was auto-accepted, provisional, or reviewed

---

## Rebuildability

Derived state should support:

- full rebuild
- selective rebuild by project
- selective rebuild by date range
- selective rebuild by provider/model
- selective rebuild by edge type
- selective rebuild for records affected by a changed ADR or Constitution

---

## Historical Interpretation

A derived edge may change over time while the original authored history remains intact.

This enables Memory Seed to distinguish:

```text
what was said
what was decided
what the system inferred at the time
what the system infers now
```

That distinction is essential for auditability.

---

## Success Condition

Memory Seed's source knowledge remains stable while its machine-generated understanding can be replaced, improved, and re-evaluated safely.
