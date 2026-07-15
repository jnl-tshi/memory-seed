---
title: "Memory Provenance and Authority Taxonomy Proposal"
date: "2026-07-15"
project: "memory-seed"
status: "promoted-to-todo"
priority: "P1"
next_action: "Reconcile the existing ProvenanceClass enum, annotation authority rules, and provider authority classes into one versioned crosswalk and fixture set before Phase 6 actionability."
related:
  - "docs/CONSTITUTION.md"
  - "docs/3_Spec/memory-trace-trail-search-and-graph-ux.md"
  - "docs/2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md"
  - "docs/2_Todo/memory-trace-structural-graph-enrichment-provider-proposal.md"
---

# Memory Provenance and Authority Taxonomy Proposal

Status: **PROMOTED to `2_Todo`** 2026-07-15; active constitutional gate before actionable annotations or generated output can influence agents.
Priority: P1 after the memory-quality trio and before Memory Trace Phase 6 actionability.
Source: JNL-approved constitutional hardening on 2026-07-15, grounded in Constitution section 7, the shipped `ProvenanceClass`, the annotation architecture, and the structural-provider proposal.
Next action: Produce an additive model/crosswalk proposal and fixtures; do not change ranking or actionability defaults in the taxonomy-definition step.

## Scope

Define separate, inspectable answers to four questions:

1. Where did this item come from? (`provenance_class`)
2. What authority does it carry? (`authority_class`)
3. What lifecycle state is it in? (record-specific status)
4. May an agent act on it now? (`actionability`, computed by policy)

## Non-goals

- No single numeric or categorical "trust score."
- No attempt to infer whether a claim is objectively true.
- No replacement of existing lifecycle edges or annotation status.
- No default ranking boost or damping.
- No automatic promotion of provider or generated content into authored memory.
- No requirement that every historical entry be backfilled.

## Dependencies

- the shipped seven-value `ProvenanceClass` in `memory-trace/memory_trace/models.py`;
- [`memory-trace-trail-search-and-graph-ux.md`](../3_Spec/memory-trace-trail-search-and-graph-ux.md);
- [`memory-trace-evidence-annotations-and-projection-architecture.md`](memory-trace-evidence-annotations-and-projection-architecture.md);
- [`memory-trace-structural-graph-enrichment-provider-proposal.md`](memory-trace-structural-graph-enrichment-provider-proposal.md);
- participant and role policy before annotations become actionable.

## Constitutional fit

Five-question contribution: **Validation + Trust + Retrieval + Application**. Capture is unchanged.

- Validation gains explicit, testable classification and actionability rules.
- Trust gains visible source and authority boundaries without pretending confidence equals truth.
- Retrieval can explain why an item is contextual, review-required, or actionable.
- Application becomes safer because agents act only on policy-qualified records.

The model preserves append-only history, attribution, model independence, Markdown authority, and the
down-rank-never-hide rule. Adopting the shipped taxonomy as Memory Seed's established trust model requires
the Constitution section 7 candidate to graduate through the amendment process; this proposal alone does
not amend the Constitution.

## Proposed model

### Axis 1 - provenance class

Keep the existing versioned API enum as the source vocabulary:

```text
authored_memory
source_control
pr_review
automation_ci
annotation
release
generated_artefact
```

Do not introduce a second event-source enum. Existing architecture shorthand such as Authored, Computed,
External, and Derived must map to this API vocabulary or to `authority_class`, not become parallel values.

### Axis 2 - authority class

Use an additive authority field for how Memory Seed treats the item's meaning:

```text
authored
computed_canonical
git_derived
provider_extracted
provider_resolved
provider_inferred
generated
```

Interpretation:

- `authored` is explicit project memory or an authorised append-only annotation.
- `computed_canonical` is deterministic output from canonical Memory Seed semantics, such as inverse edges.
- `git_derived` is deterministic repository evidence tied to a revision.
- `provider_extracted`, `provider_resolved`, and `provider_inferred` are external observations with decreasing certainty; all retain provider, revision, freshness, and source location.
- `generated` is model- or rule-generated interpretation and remains advisory until explicitly promoted.

Confidence is separate metadata. It cannot upgrade authority or actionability.

### Axis 3 - lifecycle state

Keep lifecycle status owned by the record type: entry lifecycle edges, annotation event/status, proposal
lane, provider freshness, and generated-artifact promotion state remain distinct. Do not flatten these into
the authority taxonomy.

### Axis 4 - actionability

Expose a small computed result:

```text
context_only
review_required
actionable
```

An item is `actionable` only when an explicit policy can cite all required inputs: provenance, authority,
record kind/status, participant role, freshness, conflict state, and project scope. Missing or conflicting
inputs fail closed to `review_required` or `context_only`. Generated and provider-inferred content cannot be
actionable on their own.

## Implementation sequence

1. Inventory every existing provenance, authority, confidence, lifecycle, and role field.
2. Publish a crosswalk showing canonical field ownership and deprecated aliases.
3. Add additive API models and fixtures without changing retrieval order.
4. Display provenance and authority distinctly in Trace and evidence views.
5. Implement actionability as a policy result with reason codes.
6. Run fixtures proving generated/provider content cannot silently become actionable.
7. Propose the constitutional section 7 graduation only after the behaviour ships and is evidenced.

## Acceptance criteria

- The shipped `ProvenanceClass` remains the one event-source vocabulary.
- Provenance, authority, lifecycle, confidence, and actionability are separate fields.
- Every non-authored or generated item exposes source and authority in API fixtures and UI inspection.
- Actionability includes machine-readable reason codes and fails closed when policy inputs are missing.
- Provider confidence never changes canonical importance or actionability by itself.
- Generated output remains non-authoritative until explicit, attributable promotion.
- Historical entries need no destructive backfill.
- No taxonomy field changes default ranking without exposure, fixtures, and real-corpus A/B validation.

## Promotion gate

Before Phase 6 annotations are agent-actionable or generated output influences agent instructions:

- the crosswalk and versioned contract are adopted;
- participant/role fixtures pass;
- generated/provider fail-closed fixtures pass;
- local/offline behaviour remains complete;
- the maintainer approves any constitutional amendment needed to graduate section 7.
