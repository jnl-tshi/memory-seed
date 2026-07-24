---
title: "Proposal: High-Signal Knowledge Lenses Roadmap"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
replaced_on: "2026-07-20"
replaced_by: "../4_Reference/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: High-Signal Knowledge Lenses Roadmap

**Status:** Exploratory proposal  
**Decision class:** Future capability prioritisation  
**Applies to:** Memory Seed retrieval, Memory Trace, sidecar framework, project review and agent reasoning

## 1. Purpose

Memory Seed already provides several high-value lenses:

- chronological history;
- architectural decisions;
- visual diagrams;
- derived provenance, evolution, replacement, and supersession relationships.

The purpose of this proposal is not to create a large catalogue of sidecars. It is to identify the smallest set of additional lenses most likely to reduce repeated inference and improve future decisions.

The governing test is:

> If an agent repeatedly has to infer a useful property from the timeline, and that inference changes or supports decisions, the property may justify a lens.

## 2. Evaluation dimensions

Each candidate is evaluated against:

- recurring question answered;
- decision impact;
- repeated inference removed;
- human value;
- agent value;
- feasibility;
- risk of noise;
- overlap with existing metadata or sidecars.

## 3. Priority 1: Open questions and unresolved tensions

### Question answered

- What is still unresolved?
- Which trade-off has been recognised but not settled?
- What question must be answered before this work can proceed safely?

### Why it changes decisions

A current decision can appear complete while depending on an unresolved constraint. Surfacing the tension prevents agents from treating provisional conclusions as settled architecture.

Examples:

- local-first operation versus hosted premium functionality;
- deterministic outputs versus flexible provider-specific capability;
- free trail access versus premium differentiation;
- append-only files versus mutable review state;
- Mermaid coverage versus richer interactive graph representations.

### Proposed representation

```yaml
kind: unresolved_question
question_id: question-...
question: How should premium features preserve local-first guarantees?
status: open
source_entries:
  - ...
topics:
  - monetisation
  - local-first
blocks:
  - decision-id
options:
  - ...
last_reviewed_at: ...
```

### Recommendation

Pilot first. It has high decision value, supports planning, and exposes omissions without requiring a comprehensive ontology.

## 4. Priority 2: Assumptions and validity conditions

### Question answered

- What must remain true for this decision or implementation to remain valid?
- Which conclusion depends on an unverified belief?

### Why it changes decisions

Decisions frequently become outdated because an assumption changes, not because the original reasoning was poor. A visible assumption lens creates a direct trigger for reconsideration.

Examples:

- supported providers can all return schema-conforming classifications;
- local file access remains the primary deployment model;
- Mermaid is sufficient for most static diagrams;
- deterministic anchors remain stable after document edits;
- users will tolerate the authoring overhead of required metadata.

### Proposed representation

```yaml
kind: assumption
assumption_id: assumption-...
statement: Deterministic anchors remain stable across routine document edits.
status: unverified
supports:
  - decision-id
source_entries:
  - ...
validation:
  method: ...
  last_result: ...
```

### Recommendation

High-value second pilot after unresolved questions. Its main risk is extracting too many weak or obvious assumptions.

## 5. Priority 3: Validation and evidence lens

### Question answered

- What evidence shows that this decision or implementation works?
- What remains unvalidated?
- Which benchmark, test, review, or user observation supports the claim?

### Why it changes decisions

The existence of implementation is not evidence of success. A validation lens allows release, promotion, and architectural review to distinguish:

- proposed;
- implemented;
- tested;
- validated;
- invalidated;
- inconclusive.

Entry intent already marks validation activity. This lens would aggregate the actual evidence and connect it to claims or decisions.

### Proposed representation

```yaml
kind: validation_record
validation_id: validation-...
subject:
  type: decision
  id: decision-id
result: passed
evidence:
  - entry_id: ...
    anchors:
      - benchmark-results
criteria:
  - ...
limitations:
  - ...
```

### Recommendation

Implement only after intent metadata is in use. Otherwise the lens will duplicate ad hoc inference.

## 6. Priority 4: Durable findings or learned facts

### Question answered

- What did the project learn that remains useful beyond the session in which it was discovered?
- Which factual conclusion should influence future work even though it is not an ADR?

### Why it changes decisions

Research and implementation often reveal durable facts that are neither decisions nor tasks.

Examples:

- a provider consistently omits diagram generation without an explicit contract;
- a retrieval strategy fails under a specific data shape;
- a library cannot support a required interaction;
- a packaging constraint changes the feasible upgrade workflow.

### Proposed representation

```yaml
kind: finding
finding_id: finding-...
claim: ...
scope: ...
confidence: ...
source_entries:
  - ...
implications:
  - ...
invalidated_by: []
```

### Recommendation

Valuable, but introduce cautiously. It can become a second generic summary system unless “durable and decision-relevant” is enforced.

## 7. Priority 5: Question-oriented retrieval index

### Question answered

- Which recurring question was this entry, decision, or investigation trying to answer?

### Why it changes decisions

Humans often retrieve by question rather than by terminology. The same underlying issue may be described using changing technical language, while the question remains stable.

Examples:

- How should Memory Seed remain vendor-neutral?
- What is the current source of truth for relationships?
- How is supersession represented?
- What must be free versus premium?
- How can sidecar coverage be measured?

### Proposed representation

```yaml
kind: question_index
question_id: question-...
canonical_question: How should sidecar generation remain consistent across providers?
variants:
  - How do we prevent Claude and Codex from producing different coverage?
  - What is the minimum sidecar contract?
answers:
  - sidecar-id
supporting_entries:
  - ...
status: answered
```

### Recommendation

Keep exploratory. It may become highly useful for retrieval, but canonicalising questions and tracking answer status is semantically difficult.

## 8. Lower-priority candidates

### Constraint lens

Captures hard limitations such as platform, security, encoding, dependency, budget, or local-first requirements.

Potentially useful, but constraints may be better represented as declared metadata or proposal sections before introducing a general sidecar.

### Failure and rejected-path lens

Captures approaches that were attempted and why they should not be repeated.

High value in mature projects, but may overlap with findings, validation, and ADR consequences.

### Actor and responsibility lens

Captures who owns, approves, validates, or is affected by a decision.

Useful for multi-user projects, but should likely be designed with the participant and contribution model rather than as an isolated relevance lens.

### Workflow lens

Captures reusable operational sequences.

Potentially valuable, but should be evaluated separately because workflows are executable or prescriptive artefacts rather than only retrieval lenses.

### Risk lens

Captures risk, likelihood, impact, mitigation, and trigger.

Useful for project management, but risks becoming broad and high-maintenance unless linked to explicit decision and release processes.

## 9. Recommended prioritisation

| Priority | Lens | Reason |
|---:|---|---|
| 1 | Open questions and unresolved tensions | Prevents provisional conclusions from appearing settled |
| 2 | Assumptions and validity conditions | Explains when decisions must be revisited |
| 3 | Validation and evidence | Connects implementation and decisions to proof |
| 4 | Durable findings | Promotes reusable knowledge outside ADRs |
| 5 | Question-oriented index | Potentially powerful retrieval surface, but harder to canonicalise |

## 10. Pilot method

Each new lens should be tested before becoming part of the core system.

### Pilot steps

1. Select 20–50 representative historical entries.
2. Manually identify expected lens instances.
3. Define a minimal schema.
4. Run extraction with at least two providers.
5. Measure coverage, false positives, correction rate, and token cost.
6. Test whether the lens changes retrieval or a real project decision.
7. Assess maintenance and reconciliation burden.
8. Promote, revise, or reject the lens.

### Promotion criteria

A lens should be promoted only when it demonstrates:

- repeated use;
- measurable reduction in retrieval or reasoning effort;
- acceptable provider conformance;
- reliable evidence linking;
- manageable noise;
- distinct value beyond existing metadata and sidecars.

## 11. Recommended first experiment

Pilot **open questions and unresolved tensions**.

Reasons:

- it fills a clear gap left by timeline, ADR, diagram, and relationship lenses;
- it directly changes future decisions;
- it makes uncertainty explicit;
- it supports planning without duplicating TODOs;
- it can link to decisions it blocks or qualifies;
- it provides a useful test of the general sidecar framework.

The pilot should remain non-authoritative until reviewed. The system should not automatically treat an extracted tension as a blocker without explicit policy or human confirmation.

## 12. Acceptance criteria

- The project does not adopt all candidate lenses at once.
- Open questions and unresolved tensions are selected as the first lens pilot.
- Each lens has a recurring question and decision-effect statement.
- New lenses use the common sidecar provenance and lifecycle contract.
- Promotion depends on measured decision value rather than extraction feasibility alone.
