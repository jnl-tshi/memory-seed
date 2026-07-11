---
title: "Agent Guide: Integrating the Memory Trace Next-Generation Plan"
date: "2026-07-11"
project: "memory-seed"
status: "execution-guide"
---

# Agent Guide: Integrating the Memory Trace Next-Generation Plan

> **Status:** COMPLETED 2026-07-11. The imported Memory Trace next-generation document set was
> promoted into `docs/2_Todo/` and `docs/3_Spec/`; source provenance moved to `docs/4_Reference/`;
> and the coverage/retirement decision was captured in
> [`../memory-trace-next-generation-coverage-matrix.md`](../memory-trace-next-generation-coverage-matrix.md).
> No active implementation plan was retired unless its remaining requirements were preserved
> elsewhere.

## Purpose

Fold the new Memory Trace document set into the repository as the active plan, preserve unique prior decisions, and retire only documents whose scope is fully superseded.

Do not delete history or mark unfinished work as completed.

## Read order

1. `AGENTS.md` and the nearest `.memory-seed/` runtime instructions.
2. `docs/3_Spec/functionality-audit.md`.
3. `docs/3_Spec/graph-edge-contract.md`.
4. `memory-trace-product-and-system-architecture-blueprint.md`.
5. Supporting new proposals/specifications in this set.
6. Existing Memory Trace plans named by the blueprint.
7. `docs/2_Todo/0_NEXT_STEPS.md`, proposal lifecycle guidance and current session entries.

## Integration procedure

### 1. Discover

List all existing documents matching:

```text
memory-trace
trail
lense
graph
topic-neighbourhood
timeline
summary
presentation
report
distribution
```

Record status, path and unresolved acceptance criteria.

### 2. Build a coverage matrix

For each old document, classify every substantive requirement as:

- preserved by a new document;
- implemented already;
- still unique and active;
- contradicted and requiring user decision;
- obsolete.

Never retire a document while it contains unique unresolved requirements.

### 3. Install the new document set

Place files at their proposed `docs/2_Todo/` and `docs/3_Spec/` paths. Update relative links to match the repository.

Add the blueprint to the active-plan index and `0_NEXT_STEPS.md`.

### 4. Fold unique requirements

Where an older plan contains a unique active requirement:

- add it to the correct new document;
- preserve its rationale and acceptance criteria;
- add a provenance note naming the old file;
- do not silently discard it.

### 5. Retire safely

Use these statuses:

- **Historical completed plan:** keep in `docs/2_Todo/completed/`; add `superseded_by` only if the new document now governs future work.
- **Superseded but not completed:** move to `docs/4_Reference/retired/` (create only if consistent with proposal-lifecycle policy), add:
  - `status: superseded`;
  - `superseded_by`;
  - retirement date;
  - a banner explaining that it is historical.
- **Partially superseded:** keep active and add a scope note pointing to the new canonical document.
- **Implemented specification:** keep as reference/specification; do not retire merely because a broader blueprint exists.

Do not use `completed/` for work that was abandoned or merely replaced.

## Initial retirement guidance

| Existing document | Action |
|---|---|
| `memory-trace-product-and-trail-view-plan.md` | Preserve as completed history; new blueprint/UX spec govern future evolution |
| `memory-trace-distribution-plan.md` | Keep active until remaining package/release acceptance criteria are complete; add blueprint cross-link |
| `memory-trace-ai-timeline-summarisation-plan.md` | Keep active and canonical for AI implementation; add derived-artifact contract link |
| `memory-trace-topic-neighbourhoods-plan.md` | Keep active for core topic implementation; new UX spec governs graph presentation |
| `session-decision-diagrams-plan.md` | Keep active if acceptance criteria remain; cross-link derived exports |
| `memory-seed-market-fit-report.md` | Move to reference/retired research after commercial report is installed and its source value is preserved |
| `graph-edge-contract.md` | Remains canonical; never supersede with UI documents |
| `functionality-audit.md` | Remains current-system baseline; update after implementation, not during plan installation |

Confirm actual paths and statuses before applying this table.

## Cross-reference updates

Update:

- `0_NEXT_STEPS.md`;
- relevant plan indexes;
- functionality-audit roadmap section;
- Memory Trace README planning links;
- AI summary plan references;
- topic and graph plan references.

The blueprint becomes the top-level planning entry point.

## Validation

Before committing:

- run links/reference checks;
- ensure no active plan points only to a retired file;
- confirm new docs do not redefine canonical graph semantics;
- confirm AI plan remains linked;
- confirm package/distribution constraints are retained;
- run encoding checks;
- inspect `git diff --check`;
- record the integration and retirement decisions in a session entry.

## Stop conditions

Stop and ask the user when:

- two active plans conflict;
- retirement would discard unique acceptance criteria;
- proposal-lifecycle policy has no valid superseded-document lane;
- an old plan appears implemented only on a branch not visible in the current tree;
- file movement would break external references without a redirect/stub strategy.
