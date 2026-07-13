---
title: "Memory Trace Derived-Artifact Provenance Contract"
date: "2026-07-11"
project: "memory-seed"
status: "proposed-specification"
spec_binding: candidate
related:
  - "../2_Todo/memory-trace-ai-timeline-summarisation-plan.md"
  - "../2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md"
---

# Memory Trace Derived-Artifact Provenance Contract

Status: Active proposed specification, promoted from inbox on 2026-07-11.
Priority: P3 contract before AI summaries, project updates, reports, presentations, or exports are treated as product features.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`, folded with `../2_Todo/memory-trace-ai-timeline-summarisation-plan.md`.
Scope: Derived artefact package shape, provenance manifest, claim/evidence requirements, contradiction handling, export adapters, promotion, storage, and validation.
Non-goals: No AI provider implementation, no external publishing by default, no generated artefact becoming authoritative without explicit promotion.
Dependencies: `../2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md`, `../2_Todo/memory-trace-ai-timeline-summarisation-plan.md`, and `../2_Todo/session-decision-diagrams-plan.md`.
Acceptance criteria: Every material generated claim maps to evidence, manifests validate cited entries/chunks/freshness, adapters do not invent claims, and promotion is explicit/auditable.

## 1. Purpose

This contract defines how AI summaries, project updates, reports, presentations and exports retain programmatic evidence.

It supplements the existing AI timeline-summarisation plan. It does not replace that plan's provider, safety or implementation sequencing.

## 2. Governing rule

> Every material generated claim must map to one or more cited evidence items. The human-readable output and its machine-readable appendix are one artefact.

## 3. Derived artefact classes

- timeline summary;
- Trail summary;
- decision diff;
- stakeholder handover brief;
- project update;
- report;
- presentation;
- table/CSV/XLSX;
- board-layout export.

## 4. Required package

A derived artefact consists of:

```text
artifact/
  content.<format>
  provenance.json
  evidence-pack.json or immutable pack reference
  generation.json
```

For a PPTX, `provenance.json` may be embedded and also emitted beside the file.

## 5. Provenance manifest

Minimum fields:

```json
{
  "artifact_id": "art_...",
  "artifact_type": "presentation",
  "created_at": "2026-07-11T12:00:00Z",
  "project_id": "...",
  "selection": {
    "type": "trail_range",
    "start_entry_id": "mse_a",
    "end_entry_id": "mse_b"
  },
  "claims": [
    {
      "claim_id": "claim_1",
      "artifact_location": {
        "slide": 3,
        "element": "body-1"
      },
      "evidence": [
        {
          "entry_id": "mse_a",
          "chunk_id": "mse_a#section-2",
          "source_path": ".memory-seed/sessions/...",
          "anchor": "mse_a#decision-1"
        }
      ]
    }
  ],
  "generated_by": {
    "provider": "local_openai_compatible",
    "model": "...",
    "configuration_hash": "..."
  }
}
```

## 6. Claim requirements

Material claims include:

- decisions;
- reasons;
- status assertions;
- risks;
- unresolved questions;
- chronology;
- ownership;
- test outcomes;
- implementation status;
- recommendations presented as evidence-based.

A claim with no supporting evidence must be:

- omitted;
- marked `unsupported`;
- or clearly labelled as model inference.

## 7. Evidence types

Supported evidence:

- memory entry or section;
- deterministic decision anchor;
- typed graph edge;
- file/continuity record;
- commit;
- pull request/review;
- CI result;
- authoritative decision annotation.

Private notes are excluded unless the user explicitly includes them.

## 8. Contradiction and missing evidence

The manifest records:

- contradictory sources;
- missing expected evidence;
- unavailable provider records;
- stale snapshots;
- confidence level;
- whether the statement is direct or inferred.

Generated content must not silently reconcile contradictions.

## 9. Deterministic export adapters

Adapters consume validated summary JSON and provenance data.

They may:

- format;
- paginate;
- layout;
- render charts/tables;
- embed citations.

They may not invent new uncited claims.

External publishing is opt-in and outside the core summarisation engine.

## 10. Promotion

A derived artefact is non-authoritative by default.

Promotion requires:

- explicit user action;
- destination selection;
- review status;
- provenance retention;
- a new memory entry referencing the artefact;
- no rewrite of original evidence.

## 11. Storage

Default local export:

```text
.memory-trace/exports/
```

A user-selected external directory is permitted. Generated artefacts do not belong under `sessions/`.

## 12. Validation

Validation must confirm:

- every cited entry/chunk exists;
- fingerprints match;
- provider references carry freshness state;
- each material output element has claim mappings;
- generation metadata is present;
- derived status is visible.

## 13. Acceptance criteria

- Presentations include a programmatic evidence appendix.
- Project updates link claims to chunks.
- Reports expose contradictions and missing evidence.
- Export adapters are deterministic after summary validation.
- Promotion is explicit and auditable.
