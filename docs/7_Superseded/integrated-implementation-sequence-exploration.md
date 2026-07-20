---
title: "Proposal: Integrated Implementation Sequence"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../4_Reference/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Integrated Implementation Sequence

**Status:** Proposed  
**Decision class:** Delivery plan  
**Applies to:** Adoption of the relevance and deterministic behaviour proposals

## 1. Purpose

The related proposals affect constitutional guidance, entry metadata, sidecar schemas, provider behaviour, validation, reconciliation, retrieval, and Memory Trace. Implementing all elements simultaneously would create unnecessary scope.

This document defines a narrow sequence that preserves the project's preference for controlled evolution.

## Pre-triage correction: sequence experiments before adoption

The original sequence begins by adopting architectural and constitutional language, then makes entry intent
mandatory before demonstrating that either change improves a real workflow. That order is reversed here.
Nothing in this set should amend the Constitution, create a general sidecar authority layer, or require new
entry metadata until a bounded experiment demonstrates distinct value over current capabilities.

### Phase A: baseline and overlap map

- Crosswalk every proposed capability against the current graph-edge contract, ADR sidecar foundation,
  Evidence Pack, topics, provenance taxonomy, and diagram/link sidecars.
- Remove duplicates and name one canonical owner for every surviving field and lifecycle.
- Define one user question and one failure case for each proposed pilot.

### Phase B: manual gold sets

- Hand-label a small corpus for decision identity, evidence anchors, intent, and one open-question lens.
- Measure ambiguity removed, correction rate, authoring burden, and whether the label changes retrieval or a
  review decision.
- Reject labels that merely restate headings, topics, branch names, Todo state, or DRAFT sections.

### Phase C: one narrow implementation experiment

- Implement only the strongest surviving delta behind an inspectable, opt-in read surface.
- Keep inferred or generated classifications non-authoritative and provenance-labelled.
- Compare against the current system with an unaffected control before considering default behaviour.

### Phase D: promotion decision

- Fold a successful delta into its existing owner plan or contract; do not promote this whole programme.
- Consider constitutional wording only when the experiment reveals a durable rule not already covered.
- Keep failed experiments in the lifecycle record with their evidence and kill criteria.

## 2. Phase 0: Adopt the architectural language

### Deliverables

- Add the proposed constitutional principles.
- Define `canonical`, `declared`, `derived`, `lens`, `sidecar`, `transformation`, and `promotion`.
- Document the metadata-versus-sidecar rule.
- Record that sidecars are alternate representations, not independent sources of truth.

### Exit criteria

- Future proposals can use the terms without ambiguity.
- Contributors understand why intent is metadata while ADRs are sidecars.

## 3. Phase 1: Entry intent metadata

### Deliverables

- Add `intent` to the entry schema.
- Adopt the initial controlled vocabulary:
  - `research_planning`;
  - `implementation`;
  - `validation`;
  - `decision_update`.
- Update the session logging skill.
- Add schema validation.
- Add basic intent filtering in retrieval or Memory Trace.
- Provide a non-destructive historical backfill mechanism.

### Exit criteria

- New entries consistently declare intent.
- Historical inferred intent is distinguishable from author-declared intent.
- A branch can be queried for implementation without validation.

## 4. Phase 2: ADR generation contract

### Deliverables

- Define ADR eligibility criteria.
- Require an eligibility result for relevant entries.
- Define decision-level identities when one entry contains several decisions.
- Create ADR schema validation.
- Add evidence anchors.
- Record `not_applicable`, `uncertain`, `deferred`, and `failed`.
- Add a manual ADR reconciliation command.

### Exit criteria

- Codex, Claude, and any supported provider produce the same required result shape.
- Eligible ADR omissions are detectable.
- An ADR reference identifies a specific decision, not only an entry.

## 5. Phase 3: Common sidecar manifest

### Deliverables

- Define shared sidecar lifecycle states.
- Store generation provenance and policy version.
- Add a queryable evaluation manifest.
- Add coverage reporting.
- Add stale and superseded detection.
- Align ADR, diagram, and derived-edge sidecars to the common model.

### Exit criteria

- The repository can report sidecar evaluation and generation coverage.
- A missing evaluation is distinguishable from `not_applicable`.
- Sidecars can be regenerated without losing provenance.

## 6. Phase 4: Provider conformance

### Deliverables

- Create a small fixture corpus.
- Test ADR, diagram, and relationship contracts across supported providers.
- Record schema validity, omission rate, evidence accuracy, and parse success.
- Define a minimum conformance threshold based on observed baselines.

### Exit criteria

- Provider choice affects quality but not whether required workflow steps occur.
- Non-conformant providers are clearly identified for each sidecar capability.

## 7. Phase 5: First new lens pilot

### Deliverables

- Pilot open questions and unresolved tensions.
- Use historical entries and at least two providers.
- Measure correction rate, utility, retrieval impact, and maintenance cost.
- Display the pilot lens as generated and non-authoritative.
- Decide whether to promote, revise, or reject it.

### Exit criteria

- The lens demonstrably reduces repeated inference or changes a real decision workflow.
- The project has evidence for or against extending the lens architecture.

## 8. Phase 6: Retrieval integration

### Deliverables

- Permit queries by intent and lens kind.
- Expand retrieved entries through provenance and successor edges.
- Prefer current non-superseded decisions where appropriate.
- Return compressed lens results with direct evidence links.
- Preserve access to the canonical timeline.

### Exit criteria

- Decision-oriented retrieval can surface the current decision, its provenance, its supporting validation, and unresolved qualifications.
- Retrieval behaviour remains inspectable rather than opaque.

## 9. Scope controls

The following should remain out of scope until the earlier phases are validated:

- a comprehensive ontology;
- automatic adoption of all proposed lenses;
- complex multi-intent taxonomies;
- mandatory four-stage branch workflows;
- automatic promotion of generated knowledge;
- provider-specific sidecar schemas;
- replacing canonical timeline retrieval;
- broad workflow or risk management systems.

## 10. Overall success measures

The programme should be considered successful when it produces evidence that:

- sidecar omissions are detectable;
- provider contract compliance is stable;
- retrieval returns fewer outdated decisions;
- agents spend less effort inferring intent and lifecycle stage;
- users can trace every lens back to canonical evidence;
- new lenses are admitted through measured decision value;
- the architecture remains usable without a comprehensive ontology.
