---
title: Memory Seed workflow evidence and review workbench
status: active
priority: P2
next_action: Reconstruct three completed project journeys from existing entries, documents, and Git references before defining a ReviewItem fixture.
blocked_by:
  - memory-seed-semantic-record-and-signal-foundation-plan.md
  - document-lifecycle-system-plan.md Phase 2
  - memory-provenance-and-authority-taxonomy-proposal.md
  - memory-quality-metrics-v0-proposal.md
sources:
  - ../7_Replaced/agent-workflow-observability-exploration.md
  - ../7_Replaced/idea-to-ship-trace-model-exploration.md
  - ../7_Replaced/derived-review-queue-and-document-lineage-proposal.md
---

# Workflow Evidence and Review Workbench

Status: **ACTIVE, DEPENDENCY-GATED**. This plan owns reconstruction and review of work evidence; it does
not schedule agents or establish a universal delivery process.

## Outcome

Let a human reconstruct why work happened, which evidence and decisions shaped it, what artifacts resulted,
and which bounded review questions remain. The workbench is a deterministic read model over existing
Markdown, lifecycle metadata, and Git references.

Five-question test: **Retrieval**, **Trust**, and **Application**.

## Scope

- Reconstruct three real journeys using only existing entries, documents, commits, branches, and canonical
  lifecycle links.
- Define missing references as typed artifact/provenance references, not a new generic graph vocabulary.
- Derive document-to-decision lineage from folder lifecycle state and explicit source links.
- Define a read-only `ReviewItem` only after the real journeys demonstrate repeated review needs.
- Surface source, authority, freshness, conflict, and unresolved status for every review item.

## Non-goals

- No raw agent telemetry, transcript warehouse, workflow scheduler, or universal stage sequence.
- No automatic document movement, approval, rejection, or human judgement.
- No duplication of external issue trackers or Git history as Memory Seed-owned state.
- No hidden workflow score and no ranking effect without a separate real-corpus gate.

## Sequence

1. **Corpus proof:** reconstruct three completed journeys and record which existing references suffice.
2. **Reference gap:** add only the minimum typed artifact references needed across all three.
3. **Lineage projection:** derive entry -> decision -> document -> implementation/test/release views.
4. **Review fixture:** define `ReviewItem` with source references, requested decision, evidence, authority,
   freshness, conflict state, and an optional resolution entry.
5. **Workbench:** add a human-controlled Trace view with no write or automation path.

## Acceptance criteria

- Three real journeys are explainable without inventing a universal workflow.
- Every displayed relation resolves to canonical repository evidence.
- Review items are deterministic and disappear only through an attributable resolution record.
- Rebuilding the projection from Markdown and Git produces equivalent output.
- No review state becomes agent-actionable before the provenance/actionability policy permits it.
