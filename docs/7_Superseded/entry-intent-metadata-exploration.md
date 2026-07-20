---
title: "Proposal: Entry Intent Metadata and Branch Lifecycle"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../1_Inbox/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Entry Intent Metadata and Branch Lifecycle

**Status:** Proposed  
**Decision class:** Entry schema and workflow  
**Applies to:** Session logging, branch work, retrieval, Memory Trace filters, control plane, CLI and MCP validation

## 1. Problem

A timeline entry records activity, but agents often have to infer why the activity occurred.

The same topic may appear in entries that serve very different purposes:

- exploring a problem;
- evaluating alternatives;
- planning work;
- implementing a selected approach;
- validating that the implementation works;
- updating an existing decision.

Without declared intent, an agent must reconstruct the stage from prose. That inference is repeated during retrieval, branch review, planning, and validation.

This also hides meaningful absences. A branch may contain substantial implementation work but no recorded validation. Unless the stages are explicitly represented, that gap is difficult to query reliably.

## 2. Proposal

Add a first-class, controlled `intent` field to entry YAML.

Intent is authoritative metadata because it is known by the actor creating the entry. It should not be a sidecar by default.

A compact initial vocabulary is recommended:

```yaml
intent: research_planning
```

Allowed values:

- `research_planning`
- `implementation`
- `validation`
- `decision_update`

### `research_planning`

Combines exploration, evaluation, proposal development, and planning where separating them would create unnecessary overhead.

Use when the entry:

- investigates a problem;
- compares alternatives;
- records research findings;
- proposes future work;
- defines a plan before implementation.

### `implementation`

Use when the entry records execution that changes the project, system, artefacts, or operational behaviour.

### `validation`

Use when the entry tests, reviews, verifies, measures, or otherwise evaluates whether prior work satisfies its intended requirements.

### `decision_update`

Use when the activity primarily changes, clarifies, confirms, narrows, rejects, supersedes, or extends an existing decision rather than directly evolving implementation.

This value is important because some interactions evolve decisions without evolving the implemented system.

## 3. Why intent belongs in metadata

Intent should be declared at write time because it is:

- known by the actor performing the work;
- compact;
- useful for routine filtering;
- stable enough to be authoritative;
- less costly to declare than infer;
- directly useful for branch and project lifecycle analysis.

This follows the architectural rule:

> Constrain what is known; derive what is discovered.

A sidecar may later derive additional interpretations, but it should not replace the declared intent.

## 4. Intent is not entry type

Intent and entry type should remain conceptually separate.

- **Type** describes the structural or content category of an entry.
- **Intent** describes why the work represented by the entry was performed.

For example:

```yaml
type: session_entry
intent: validation
topics:
  - retrieval
  - reranking
```

Or:

```yaml
type: decision_record
intent: decision_update
```

Keeping the two fields separate prevents a type taxonomy from becoming overloaded with workflow semantics.

## 5. Branch lifecycle as a computed view

Do not create a branch lifecycle sidecar solely to repeat entry intent.

Instead, compute branch state from the sequence of entries.

Example:

```text
research_planning → implementation → validation
```

Possible computed states:

- research only;
- planned, not implemented;
- implementation in progress;
- implemented, validation absent;
- validation in progress;
- validated;
- decision updated after implementation;
- mixed or non-linear;
- insufficient evidence.

The lifecycle must remain descriptive rather than prescriptive.

## 6. No forced four-stage workflow

Not every branch requires every intent.

Examples:

- a documentation-only branch may use `implementation` and `validation`;
- a research branch may contain only `research_planning`;
- a correction to an ADR may use only `decision_update`;
- an obvious maintenance change may use `implementation` and `validation` without separate research;
- a failed experiment may end with `validation` and no production implementation.

The system should support:

- absent because not needed;
- absent because not yet completed;
- absent because not recorded;
- explicitly not applicable where a policy requires evaluation.

A branch should not be penalised merely for not matching a linear template.

## 7. Entry schema

Initial form:

```yaml
---
entry_id: ...
created_at: ...
author: ...
branch: ...
intent: implementation
topics:
  - sidecars
  - agent-consistency
---
```

Optional extension:

```yaml
intent:
  primary: implementation
  secondary:
    - decision_update
```

The initial implementation should prefer a single value. Multi-intent support should be introduced only if repository evidence shows that one primary intent is regularly insufficient.

## 8. Validation rules

The CLI and MCP tooling should validate:

- `intent` exists for newly written entries after adoption;
- the value belongs to the controlled vocabulary;
- aliases or spelling variations are rejected or normalised;
- historical entries may remain unclassified until reconciliation;
- generated entries identify whether intent was author-declared or inferred during backfill.

Suggested commands:

```text
memory-seed entries check-intent
memory-seed entries backfill-intent
memory-seed branch lifecycle <branch>
memory-seed branch gaps <branch>
```

## 9. Historical backfill

Intent can be added retroactively, but the system should preserve provenance.

Example:

```yaml
intent:
  value: validation
  source: inferred
  inferred_at: 2026-07-18T17:00:00Z
  confidence: 0.84
  policy_version: "1"
```

Author-declared intent should remain distinguishable:

```yaml
intent:
  value: validation
  source: declared
```

A reviewed inferred value may be promoted:

```yaml
intent:
  value: validation
  source: reviewed
```

For simplicity, this richer structure may be stored in an index or migration record while the entry retains a compact scalar.

## 10. Retrieval and interface value

Intent enables queries such as:

- show validation evidence for this feature;
- find research that preceded this ADR;
- retrieve implementation entries linked to this decision;
- show decision updates since the last release;
- identify branches with implementation but no validation;
- compare planned work with completed work;
- rank validation entries higher during release review.

Memory Trace can expose intent as:

- filters;
- badges;
- branch progress summaries;
- timeline groupings;
- missing-stage warnings;
- retrieval constraints.

## 11. Interaction with ADRs and sidecars

Intent does not replace ADR extraction.

- `decision_update` indicates that the entry's purpose concerns a decision.
- The ADR sidecar identifies and represents the specific architecturally significant decision.
- Not every `decision_update` is architectural.
- An architectural decision may be supported by `research_planning`, `implementation`, or `validation` entries in addition to a `decision_update`.

Intent should therefore be an input signal for ADR eligibility, not a substitute for it.

## 12. Risks

### Intent is selected mechanically

Mitigation: clear definitions, examples, and validation fixtures.

### Too many intent values

Mitigation: retain a small core and require evidence before adding another value.

### Agents misclassify intent

Mitigation: the acting agent declares intent, but reconciliation can flag inconsistencies between metadata and content.

### Branch state becomes a gate

Mitigation: lifecycle views are descriptive by default. Policies may require validation only for explicitly defined release or risk classes.

## 13. Acceptance criteria

- New entries support a controlled `intent` field.
- The initial vocabulary contains no more than the four proposed values.
- Intent is documented as distinct from entry type.
- Branch state is computed rather than duplicated into a new authoritative sidecar.
- Missing validation or other meaningful gaps can be queried.
- Historical inferred intent is distinguishable from declared intent.
- ADR extraction can use intent as one eligibility signal.
