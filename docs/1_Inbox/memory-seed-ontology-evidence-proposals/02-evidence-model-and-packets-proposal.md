# Proposal: Evidence as a First-Class Model and Compact Packet

**Status:** Explore further before promotion to ADR  
**Date:** 2026-07-18  
**Related documents:** [Ontology](01-memory-seed-ontology-proposal.md), [Supersession](03-decision-supersession-and-evolution-proposal.md), [Context Assembly](04-deterministic-context-assembly-proposal.md)

## Summary

Memory Seed should represent evidence as an addressable, traceable concept linked to specific decisions or claims.

For model interaction, relevant evidence should be assembled into compact evidence packets. These packets should provide the smallest sufficient set of facts, sources, qualifications, and decision history needed for the current task.

## Problem

Decision records often explain a conclusion in prose but do not clearly separate:

- the decision;
- the claims on which it depends;
- the evidence supporting those claims;
- conflicting evidence;
- assumptions;
- the scope and freshness of the evidence;
- the reason an earlier decision is no longer valid.

This makes later review expensive. Humans and agents must reread entire documents and infer which passages justify which conclusion.

It also weakens supersession. A later decision may replace an earlier one without making the causal evidence explicit.

## Proposal

Introduce:

1. A minimal evidence schema.
2. Explicit evidence-to-decision or evidence-to-claim links.
3. Evidence roles such as support, contradiction, and qualification.
4. Evidence packets assembled for a specific task.
5. Validation rules for provenance, relevance, and freshness.

## Evidence definition

Evidence is a traceable item that changes the reasonable confidence, scope, or interpretation of a claim or decision.

Evidence is not synonymous with a source. A source is where information came from. Evidence is the relevant observation, result, or fact extracted from that source and connected to a specific proposition.

## Minimal evidence schema

```yaml
evidence:
  - id: ev-2026-07-18-01
    summary: Retrieval tests returned the same decision set across five repeated runs.
    role: supports
    target: dec-2026-07-18-01
    source:
      type: test-result
      locator: artifacts/benchmarks/retrieval-repeatability.json
    observed_at: 2026-07-18
    confidence: high
    scope: deterministic relationship traversal
```

## Recommended fields

| Field | Required initially | Purpose |
|---|---:|---|
| `id` | Yes | Stable reference |
| `summary` | Yes | Compact evidence statement |
| `role` | Yes | `supports`, `contradicts`, `qualifies`, or `context` |
| `target` | Yes | Decision or claim affected |
| `source.type` | Yes | Test, document, code, user statement, external source, observation |
| `source.locator` | Yes where available | Provenance |
| `observed_at` | Recommended | Freshness and timeline |
| `confidence` | Recommended | Evidence quality, not decision confidence |
| `scope` | Recommended | Boundary of applicability |
| `extract` | Optional | Small source excerpt or structured value |
| `created_by` | Optional | Human or agent attribution |
| `valid_until` | Optional | Explicit expiry where appropriate |
| `method` | Optional | How evidence was produced |
| `limitations` | Optional | Known weaknesses |

## Evidence roles

### Supports

Raises confidence in the target claim or decision.

### Contradicts

Provides a reason to reject or revisit the target.

### Qualifies

Limits where, when, or to whom the target applies.

### Context

Improves interpretation but does not materially change confidence.

The distinction should be used in retrieval and presentation. Contradictory and qualifying evidence must not be hidden by an evidence summarizer.

## Embedded, sidecar, or hybrid storage

### Embedded evidence

Evidence appears inside the ADR or entry.

**Advantages**
- Readable in isolation.
- Versioned with the decision.
- Low resolution overhead.

**Disadvantages**
- Repeated evidence across decisions.
- Larger documents.
- Harder to update shared evidence.

### Evidence sidecar

Evidence is stored separately and linked by ID.

**Advantages**
- Reusable and independently addressable.
- Better for generated test results and external artifacts.
- Supports dedicated indexes and validation.

**Disadvantages**
- More indirection.
- Risk of broken links.
- Harder to review in plain Markdown alone.

### Recommended direction: hybrid

Use embedded evidence for the small, human-readable justification of a decision. Use sidecars or referenced artifacts for detailed, reusable, generated, or high-volume evidence.

The ADR remains understandable without resolving every sidecar, while agents can retrieve the deeper evidence when required.

## Proposed ADR evidence section

```markdown
## Evidence

### EV-01 — Retrieval repeatability
- **Role:** Supports
- **Target:** DEC-02
- **Summary:** Typed relationship traversal returned the same candidate set across repeated runs.
- **Source:** `artifacts/benchmarks/retrieval-repeatability.json`
- **Scope:** Relationship traversal only; semantic reranking remains stochastic.
- **Confidence:** High

### EV-02 — Authoring burden
- **Role:** Qualifies
- **Target:** DEC-02
- **Summary:** Three of ten entries required manual correction of decision identifiers.
- **Source:** `artifacts/pilots/ontology-authoring-review.md`
- **Confidence:** Medium
```

## Evidence packet

An evidence packet is a generated task-specific view, not a new source of truth.

A packet should normally contain:

```yaml
packet:
  task: Explain why dec-0042-02 was superseded
  subject:
    decision_id: dec-0042-02
    title: Reserve D2 for unique use cases
    status: superseded

  active_successor:
    decision_id: dec-0067-01
    relationship: supersedes
    scope: all

  evidence:
    - id: ev-0067-01
      role: supports
      summary: Maintenance cost exceeded the benefit of retaining a second diagram syntax.
      source: benchmark-2026-06-diagram-tooling

    - id: ev-0067-02
      role: qualifies
      summary: D2 remains acceptable for legacy diagrams that cannot be represented adequately in Mermaid.

  provenance:
    generated_by: context-policy-v1
    generated_at: 2026-07-18T18:30:00+01:00
    policy_hash: sha256:...
```

## Packet design principles

1. **Task-specific:** include evidence relevant to the actual question.
2. **Minimal but sufficient:** remove redundancy, not necessary qualifications.
3. **Traceable:** every material statement resolves to a source.
4. **Balanced:** include relevant contradiction and qualification.
5. **Ordered:** present decisive evidence before background context.
6. **Bounded:** declare omitted evidence, limits, and truncation.
7. **Reproducible:** record the assembly policy and source versions.

## Evidence selection tiers

A packet can use a deterministic tiered policy:

1. Direct evidence linked to the target decision.
2. Evidence linked to the superseding or dependent decision.
3. Evidence linked to the exact claims referenced.
4. Relevant contradictions and qualifications.
5. Necessary definitions and active constraints.
6. Semantic additions only when deterministic links are insufficient.

This structure limits token use while preserving causal explanation.

## Validation rules

The CLI and MCP tooling should eventually validate:

- every evidence ID is unique;
- every target exists;
- every source locator resolves where resolution is expected;
- evidence role is valid;
- evidence summaries do not exceed a configurable size;
- superseding decisions include at least one rationale or evidence reference;
- expired evidence is not silently treated as current;
- contradictory evidence is surfaced during context assembly;
- generated packets record provenance.

## Evidence quality dimensions

Evidence confidence should not be a single unexplained score. It may be derived from:

- source authority;
- directness;
- reproducibility;
- recency;
- sample adequacy;
- methodological clarity;
- independence from the decision author;
- consistency with other evidence.

The first implementation can use `low`, `medium`, and `high`, provided the author states the limitation where confidence is material.

## Expected benefits

- More grounded decision histories.
- Better explanations of supersession.
- Smaller context packages.
- Clearer audit trails.
- Reduced hallucination caused by missing qualifications.
- Better benchmark construction.
- Reusable evidence across ADRs, proposals, sessions, tests, and Memory Trace.

## Risks and mitigations

### Risk: Evidence becomes bureaucratic

**Mitigation:** require structured evidence only for consequential decisions, supersession, disputed claims, and benchmarked workflows.

### Risk: Evidence summaries misrepresent sources

**Mitigation:** retain stable provenance and permit source inspection.

### Risk: Confidence labels imply false precision

**Mitigation:** keep the scale coarse and require limitations for consequential evidence.

### Risk: Packets omit inconvenient evidence

**Mitigation:** explicitly retrieve contradictions and log packet composition.

### Risk: Packet generation becomes another stochastic summarization step

**Mitigation:** prefer extraction, typed traversal, and deterministic ordering before generative compression.

## Questions for exploration

1. Which decision types require an evidence section?
2. Should evidence IDs be repository-global or entry-local?
3. How should repeated evidence be deduplicated?
4. When may an evidence summary be generated automatically?
5. How should private, restricted, or unavailable evidence be represented?
6. Should comments and user feedback count as evidence, observations, or claims?
7. How should evidence freshness affect retrieval?

## Recommended prototype

Select five existing ADRs:

- two still active;
- two superseded or materially updated;
- one disputed or uncertain.

Add embedded evidence sections and optional detailed sidecars. Build a command that returns an evidence packet for a given decision ID.

Evaluate:

- packet size;
- proportion of packet content used in the final answer;
- correctness of cited rationale;
- missing contradictory evidence;
- authoring burden;
- repeatability.

## Promotion criteria

1. A user can explain a decision change using only the packet and linked sources.
2. Evidence items remain understandable outside the originating entry.
3. Packets consistently include relevant qualifications and contradictions.
4. Evidence linkage reduces irrelevant retrieval compared with whole-document retrieval.
5. The authoring and maintenance burden is acceptable.
