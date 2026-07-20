---
title: "Proposal: Constitutional Principles for Decision Efficiency"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../4_Reference/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Constitutional Principles for Decision Efficiency

**Status:** Candidate constitutional additions; validate before adoption  
**Date:** 2026-07-18  
**Related documents:** [Index](memory-seed-ontology-evidence-set-index-exploration.md), [Benchmarking](benchmarking-decision-quality-exploration.md)

## Summary

Memory Seed should adopt a small set of constitutional principles that direct every component toward lower decision effort, stronger evidence grounding, and more predictable behaviour.

These principles should guide architecture without prescribing one storage format or implementation.

## Candidate constitutional statement

> Memory Seed exists to improve the quality and continuity of project decisions by preserving their context, evidence, evolution, and consequences in a form that humans and agents can retrieve with minimal unnecessary effort.

## Candidate principles

## 1. Every component should reduce decision effort

A component must reduce at least one of:

- information search;
- ambiguity;
- repeated interpretation;
- stale-decision risk;
- manual cross-referencing;
- context volume;
- verification effort;
- coordination effort.

A feature that adds representational richness but does not reduce decision effort requires stronger justification.

### Test

> Which decision becomes easier, safer, faster, or more reliable because this component exists?

If the answer is unclear, the feature is likely premature.

## 2. Important decisions must remain explainable

A decision should be reconstructable from:

- the conclusion;
- the relevant context;
- the evidence;
- the constraints;
- the alternatives where material;
- the actor or process responsible;
- the later changes affecting it.

Explainability applies to historical decisions as well as active ones.

## 3. Supersession must preserve causality

A later decision must not merely replace an earlier one. It should state what changed, why it changed, and what evidence or constraint justified the change.

The system must preserve the earlier record rather than rewriting history.

## 4. Evidence should be proportional to consequence

Not every note requires a formal evidence model. The stronger the decision's consequence, irreversibility, reach, uncertainty, or dispute, the stronger its evidence requirements should be.

This avoids both evidence theatre and evidence absence.

## 5. Context should be minimal but sufficient

Memory Seed should prefer the smallest context package that preserves:

- correctness;
- material qualifications;
- relevant contradictions;
- provenance;
- active decision state.

Minimality must never be optimized independently of sufficiency.

## 6. Deterministic structure should reduce stochastic choice

Where a fact can be resolved through stable identity, explicit relationships, validation, or lifecycle rules, it should not be left entirely to model inference.

Models should reason over a prepared decision surface rather than repeatedly reconstructing the project model from raw prose.

## 7. Generated views must not become hidden sources of truth

Indexes, trails, graphs, evidence packets, summaries, and status views should be reproducible from canonical records or explicitly marked as authored records.

Derived views must expose their provenance and generation policy.

## 8. Historical truth and current truth must coexist

The system must preserve what was believed or decided at the time while making the currently active position easy to resolve.

Historical records should not be silently rewritten to match present knowledge.

## 9. Structure must earn its maintenance cost

Every mandatory field, entity, relationship, index, sidecar, or validation rule should demonstrate practical value through retrieval, explanation, governance, interface behaviour, or benchmarking.

Unused structure should be removed.

## 10. Benchmark the behaviour the system is intended to create

The project should test whether Memory Seed actually improves:

- active-decision resolution;
- evidence grounding;
- decision continuity;
- context efficiency;
- retrieval stability;
- impact awareness;
- human and agent decision effort.

Implementation completeness is not evidence of system effectiveness.

## Decision-quality rule

A concise cross-cutting rule may be:

> Prefer designs that increase decision quality under constrained context.

This rule combines quality, grounding, and efficiency without reducing success to token count.

## Evidence-grounding rule

A second rule may be:

> Consequential claims and decision changes must be traceable to sufficient evidence, explicit assumptions, or declared uncertainty.

This allows a decision to proceed under uncertainty while preventing unsupported certainty.

## Determinism rule

A third rule may be:

> Resolve identity, lifecycle, relationships, permissions, and required context deterministically wherever the project has sufficient structure to do so.

This does not prohibit semantic search or model reasoning. It defines where they should begin.

## Application checklist

Before accepting a feature or schema change, ask:

1. Which decision workflow does it improve?
2. What ambiguity or effort does it remove?
3. What is the minimum structure required?
4. Can the output be traced to canonical records?
5. Does it preserve historical and active truth?
6. How does it behave when evidence is incomplete?
7. What decision does it force an agent to make that tooling could resolve?
8. How will its benefit be benchmarked?
9. What failure mode does it introduce?
10. Can it be removed later without corrupting project history?

## Example application: Evidence sidecars

### Constitutional support

- Improve explainability.
- Preserve causality.
- Enable minimal sufficient packets.
- Reduce repeated source reading.

### Constitutional challenge

- Add indirection and maintenance cost.
- May become stale or detached.
- Could duplicate embedded ADR rationale.

### Result

Use a hybrid design only where evidence is reusable, generated, detailed, or independently versioned. Keep the human-readable decision justification embedded.

## Example application: New relationship type

A proposed relationship should be rejected unless it enables at least one distinct operation such as validation, filtering, traversal, status resolution, permissions, impact analysis, or benchmark construction.

## Governance

Constitutional additions should have a higher adoption threshold than ordinary proposals.

Before adoption:

1. Test the principle against at least three real design choices.
2. Identify a case where following it produces a meaningful trade-off.
3. Confirm that it does not duplicate an existing rule.
4. Define how violations would be detected.
5. Define whether the rule is absolute, default, or heuristic.

## Proposed classification

| Principle | Suggested strength |
|---|---|
| Every component should reduce decision effort | Default |
| Important decisions must remain explainable | Strong default |
| Supersession must preserve causality | Requirement |
| Evidence should be proportional to consequence | Default |
| Context should be minimal but sufficient | Requirement |
| Deterministic structure should reduce stochastic choice | Strong default |
| Generated views must not become hidden sources of truth | Requirement |
| Historical and current truth must coexist | Requirement |
| Structure must earn its maintenance cost | Default |
| Benchmark intended behaviour | Strong default |

## Risks

### Constitution becomes too broad

Broad statements can support conflicting choices.

**Mitigation:** attach practical tests and examples.

### Constitution blocks experimentation

Permanent rules may prevent useful prototypes.

**Mitigation:** distinguish requirements, strong defaults, defaults, and heuristics.

### Principles become slogans

Rules may be cited without measurable effect.

**Mitigation:** connect each principle to validation and benchmark evidence.

### Too many principles

A long constitution increases decision effort.

**Mitigation:** adopt only the smallest set that changes behaviour.

## Questions for exploration

1. Which principles already exist in the project constitution?
2. Should “reduce decision effort” be the top-level rule or a derived test?
3. Is “decision quality under constrained context” a principle, objective, or benchmark?
4. Which principles must be machine-checkable?
5. How should agents report constitutional trade-offs?
6. What evidence is required to modify the constitution?

## Recommended adoption sequence

### Adopt first, subject to project review

- Context should be minimal but sufficient.
- Supersession must preserve causality.
- Generated views must not become hidden sources of truth.
- Historical and current truth must coexist.

### Trial as strong defaults

- Every component should reduce decision effort.
- Deterministic structure should reduce stochastic choice.
- Benchmark intended behaviour.
- Evidence should be proportional to consequence.

### Keep as an evaluation objective

- Increase decision quality under constrained context.

## Promotion criteria

1. The principles have been compared with the existing constitution.
2. Each adopted principle has an operational test.
3. At least one real trade-off has been evaluated per principle.
4. The final set is small enough to remember and apply.
5. Benchmark results support the claims about decision effort and constrained context.
