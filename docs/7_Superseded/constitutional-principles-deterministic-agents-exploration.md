---
title: "Proposal: Constitutional Principles for Deterministic Agent Systems"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../1_Inbox/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Constitutional Principles for Deterministic Agent Systems

**Status:** Proposed  
**Decision class:** Project constitution  
**Applies to:** Memory Seed, Memory Trace, CLI, MCP tools, agent skills, sidecar generation, reconciliation, and future automation

## 1. Problem

Memory Seed is designed to be used by stochastic agents from multiple providers. Different models may:

- recognise different architectural decisions;
- create different sidecars from the same evidence;
- omit outputs that another model would generate;
- interpret prompts and project conventions differently;
- vary in quality across diagrams, ADRs, relationship extraction, and summarisation.

This variance is inherent. The project should not attempt to eliminate stochastic reasoning, but it must prevent critical correctness and coverage requirements from depending solely on model intuition.

The project also risks accumulating representations that store more information without making decisions easier. A new component is not valuable merely because it captures data. It should reduce the effort required to reach a correct, traceable conclusion.

## 2. Proposed constitutional principles

### Principle 1: Prefer deterministic system behaviour when correctness or consistency matters

> When a behaviour is required for correctness, interoperability, auditability, or minimum coverage, enforce it through schemas, controlled vocabularies, validation, explicit policies, and deterministic tooling rather than relying solely on agent discretion.

This does not prohibit model reasoning. It defines where model reasoning may operate.

Examples:

- an agent may decide whether an entry appears to contain an architectural decision;
- the system must deterministically require a classification result;
- the system must validate the result against a schema;
- the system must record whether an ADR sidecar was created, rejected, deferred, or marked not applicable;
- the system must be able to identify missing classifications later.

### Principle 2: Constrain what is known; derive what is discovered

> Information known authoritatively at the point of writing should be declared and constrained in canonical metadata. Information discovered through interpretation, aggregation, reverse-linking, or later analysis should be derived into traceable sidecars.

This principle creates a clear boundary:

- **known at write time** → canonical metadata;
- **inferred later** → derived representation;
- **derived but later confirmed** → eligible for explicit promotion.

Examples:

- the entry's intent is declared;
- the entry's author is declared;
- an explicit `evolves` link may be declared;
- reverse links such as `evolved-by` are derived;
- an ADR may be inferred from one or more entries;
- an assumption may be extracted retroactively.

### Principle 3: Every component should reduce the effort required to reach a well-supported decision

> A component, representation, or automation should be justified by the decision effort it removes, while preserving sufficient evidence, provenance, and uncertainty for the decision to remain defensible.

This principle is deliberately stronger than “make information easier to find.” It requires the project to consider:

- whether the component changes or supports a future decision;
- how much repeated inference it removes;
- whether it reduces token, cognitive, or navigation cost;
- whether it preserves the evidence needed to verify its output;
- whether it introduces more maintenance cost than decision value.

### Principle 4: Optimise for reasoning, not storage

> Memory Seed should prioritise representations that improve contextual reasoning over representations that merely increase captured information.

A timeline can contain all historical facts and still be difficult to reason over. Lenses are justified when they compress the path from evidence to conclusion without severing provenance.

### Principle 5: Derived knowledge must remain traceable to canonical evidence

> No sidecar, summary, diagram, or inferred relationship should become an ungrounded parallel source of truth.

Each derived artefact should identify:

- the source entry or entries;
- the transformation that produced it;
- the time and tool version used;
- whether it is generated, reviewed, or promoted;
- unresolved uncertainty;
- any superseding artefact.

### Principle 6: Absence should be queryable when the absence is meaningful

> Where a workflow expects a classification, validation, or decision checkpoint, the system should distinguish “not present,” “not applicable,” “not yet evaluated,” and “evaluation failed.”

This avoids silent gaps. For example, a branch with implementation entries but no validation entry is different from a branch whose validation is explicitly marked not applicable.

### Principle 7: Model capability differences should affect quality, not contract compliance

> Providers may produce outputs of different quality, but every supported provider should satisfy the same minimum output contract.

Claude, Codex, local models, and future providers may differ in diagram quality or ADR sensitivity. They should not differ in whether:

- eligibility is evaluated;
- required fields are returned;
- unsupported cases are surfaced;
- evidence links are preserved;
- validation can be run.

## 3. Constitutional wording

The following wording is suitable for direct inclusion in the project constitution:

### Deterministic behaviour

> Prefer deterministic system behaviour over emergent model behaviour whenever correctness, consistency, interoperability, or auditability matters. Use models for interpretation, but use explicit contracts, schemas, validation, and reconciliation to enforce required behaviour.

### Declared and derived knowledge

> Constrain what is known; derive what is discovered. Record authoritative information at the point of writing and represent later inference as traceable derived knowledge until it is explicitly promoted.

### Decision effort

> Every component should reduce the effort required to reach a well-supported decision. New representations must justify their cognitive, token, operational, and maintenance cost through measurable decision value.

### Evidence preservation

> Derived knowledge must remain connected to canonical evidence. Compression may shorten the route to a conclusion, but it must not remove the route back to the source.

## 4. Consequences

### Positive consequences

- More consistent behaviour across agent providers.
- Clearer criteria for deciding between entry metadata and sidecars.
- Measurable coverage rather than subjective impressions.
- Less repeated inference during retrieval.
- Reduced risk of attractive but ungrounded summaries becoming authoritative.
- A stable philosophy for evaluating future features.

### Costs and trade-offs

- Additional schemas and validation logic.
- More explicit “not applicable” or “unknown” states.
- Reconciliation jobs and conformance tests require maintenance.
- Some model flexibility is intentionally constrained.
- Feature proposals must demonstrate decision value rather than novelty.

## 5. Practical decision test

Before adding a new field, sidecar, index, or transformation, ask:

1. What recurring question does this answer?
2. Who benefits: human, agent, or both?
3. Is the information known at write time or inferred later?
4. What repeated inference does it remove?
5. Can the output change or support a decision?
6. What evidence must remain accessible?
7. What happens when the output is absent or uncertain?
8. Can all supported providers satisfy the same minimum contract?
9. Can its value and coverage be measured?
10. Is the decision value greater than its maintenance cost?

A proposal that cannot answer these questions should remain exploratory.

## 6. Acceptance criteria

This proposal is complete when:

- the principles are included in the project constitution or its governing equivalent;
- contributor and agent guidance references the principles;
- architecture proposals use the practical decision test;
- sidecar and metadata decisions explicitly identify whether knowledge is declared or derived;
- required agent behaviours are expressed as contracts rather than informal expectations.
