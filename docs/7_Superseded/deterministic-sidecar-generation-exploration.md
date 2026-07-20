---
title: "Proposal: Deterministic Sidecar Generation and Reconciliation"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../1_Inbox/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Deterministic Sidecar Generation and Reconciliation

**Status:** Proposed  
**Decision class:** Reliability and provider interoperability  
**Applies to:** ADR extraction, diagram generation, derived relationships, future sidecars, agent skills, CLI and MCP validation

## 1. Problem

Different LLMs exhibit different tendencies. One model may readily generate Mermaid diagrams while another rarely does so. One may identify ADR-worthy decisions reliably while another may omit them.

If sidecar generation is left to model intuition, Memory Seed develops silent and provider-dependent gaps:

- an eligible entry may never be evaluated;
- a provider may skip a required sidecar;
- there may be no record of whether the sidecar was unnecessary or merely forgotten;
- project coverage may change when the user switches providers;
- historical entries may remain incomplete indefinitely.

The target should not be identical creative output across providers. The target should be consistent compliance with a minimum behavioural contract.

## 2. Proposal

Move sidecar creation from an implicit model habit to an explicit extraction pipeline with four separate stages:

1. **Eligibility evaluation**
2. **Generation or structured rejection**
3. **Validation**
4. **Reconciliation**

The system owns the workflow. The model performs bounded interpretation within it.

## 3. Stage 1: Eligibility evaluation

Every applicable entry or entry set should receive an explicit eligibility result for each enabled sidecar type.

Example:

```yaml
eligibility:
  sidecar_kind: adr
  result: eligible
  confidence: 0.91
  reasons:
    - introduces a durable architecture boundary
    - replaces an earlier retrieval strategy
  decision_candidates:
    - local_api_and_mcp_as_adapters
```

Permitted results:

- `eligible`;
- `not_applicable`;
- `uncertain`;
- `deferred`;
- `failed`.

An absent result is a system gap, not equivalent to `not_applicable`.

### Deterministic pre-filters

Where useful, deterministic rules should identify entries that must be evaluated. Examples:

- entry metadata intent is `decision_update`;
- explicit relationship uses `supersedes`, `replaces`, or `evolves`;
- the entry contains a proposal acceptance;
- architecture paths, dependencies, interfaces, persistence, security, or deployment boundaries changed;
- the branch has an implementation entry whose rationale references a decision.

Rules should trigger evaluation, not automatically declare an ADR in all cases.

## 4. Stage 2: Generation or structured rejection

When eligible, the provider must return a schema-conforming sidecar or a structured reason that generation cannot proceed.

Examples of valid non-generation:

- insufficient evidence;
- conflicting entries;
- decision identity is ambiguous;
- source is incomplete;
- diagram would duplicate an existing representation;
- provider cannot render the requested syntax reliably.

This prevents silent omission.

## 5. Stage 3: Validation

Validation should be split into deterministic and semantic checks.

### Deterministic validation

Examples:

- schema validity;
- required fields present;
- referenced entry IDs exist;
- anchors resolve;
- sidecar IDs are unique;
- Mermaid parses;
- edge types belong to the controlled vocabulary;
- source entry hashes or versions match expectations;
- no circular supersession chain is introduced;
- sidecar status is valid.

### Semantic validation

Examples:

- the stated decision is supported by the evidence;
- consequences reflect the source;
- the diagram represents the referenced structure;
- a derived relationship is plausible;
- a sidecar duplicates or conflicts with another sidecar.

Semantic validation may use a second model, deterministic heuristics, human review, or a combination. It must still return a structured result.

## 6. Stage 4: Reconciliation

A reconciliation process should periodically scan current and historical entries for:

- entries never evaluated for enabled sidecars;
- eligible entries with missing sidecars;
- sidecars whose evidence no longer resolves;
- stale sidecars after source changes;
- conflicting or duplicated ADRs;
- invalid Mermaid;
- outdated policy versions;
- provider-specific coverage anomalies;
- derived relationships that should be recalculated;
- promoted facts that no longer match their derived source.

Reconciliation may run:

- after session logging;
- before release;
- on explicit CLI or MCP request;
- after changing an extraction policy;
- during repository audits.

Suggested commands:

```text
memory-seed sidecars check
memory-seed sidecars reconcile
memory-seed sidecars reconcile --kind adr
memory-seed sidecars reconcile --branch <branch>
memory-seed sidecars coverage
```

Equivalent MCP tools should expose machine-readable results.

## 7. Minimum viable acceptable criteria

Each sidecar kind should define minimum viable acceptable criteria independent of model provider.

### ADR example

An ADR-capable provider must:

- evaluate every required entry;
- identify the specific decision rather than treating the entire entry as one decision;
- link evidence;
- capture context, decision, rationale, and consequences;
- identify superseded or related decisions when known;
- return uncertainty instead of fabricating missing details;
- satisfy the ADR schema.

### Diagram example

A diagram-capable provider must:

- evaluate whether a diagram adds distinct value;
- choose an allowed diagram type;
- generate parseable Mermaid when Mermaid is selected;
- link the diagram to source entries and a described purpose;
- avoid duplicating an equivalent current diagram;
- return a structured inability result when generation fails.

The criteria should measure **contract compliance**, not whether every provider produces equally sophisticated output.

## 8. Provider conformance suite

Create a small, versioned fixture set containing:

- clear ADR-positive entries;
- clear ADR-negative entries;
- ambiguous decisions;
- multiple decisions in one entry;
- decisions spread across several entries;
- diagram-positive and diagram-negative cases;
- supersession and evolution chains;
- malformed or incomplete evidence.

For each supported provider, measure:

- eligibility classification coverage;
- schema validity;
- evidence-link accuracy;
- omission rate;
- false-positive rate;
- false-negative rate;
- parse success;
- decision identity accuracy;
- consistency across repeated runs.

Providers that fail the minimum contract may still be used for general reasoning, but should not be treated as conformant sidecar generators.

## 9. Sidecar manifest

A manifest should make coverage visible.

Example:

```yaml
sidecar_manifest:
  policy_version: "1"
  entry_id: 2026-07-18-example
  evaluations:
    adr:
      status: eligible
      sidecar_id: adr-local-adapters
      checked_at: 2026-07-18T17:00:00Z
    diagram:
      status: not_applicable
      checked_at: 2026-07-18T17:00:03Z
    derived_edges:
      status: generated
      sidecar_id: edges-2026-07-18-example
```

The manifest may be stored centrally, per entry, or as part of the sidecar index. The important requirement is that evaluation state is queryable.

## 10. Coverage metrics

Recommended metrics:

| Metric | Meaning |
|---|---|
| Evaluation coverage | Percentage of applicable entries with an explicit eligibility result |
| Eligible generation coverage | Percentage of eligible cases with a valid sidecar or structured failure |
| Schema validity | Percentage of generated sidecars passing deterministic validation |
| Evidence resolution | Percentage of references and anchors that resolve |
| Reconciliation debt | Count of unresolved stale, missing, or conflicting artefacts |
| Provider omission rate | Required evaluations or outputs silently omitted |
| Human correction rate | Percentage of generated sidecars materially changed during review |
| Superseded-sidecar accuracy | Percentage correctly identified as current or superseded |

Coverage targets should initially establish a baseline rather than impose arbitrary thresholds. Minimum release thresholds can be added after observing real repository behaviour.

## 11. Failure handling

The pipeline must prefer explicit incompleteness over false certainty.

Recommended states:

- `generated`;
- `validated`;
- `reviewed`;
- `promoted`;
- `not_applicable`;
- `uncertain`;
- `failed`;
- `stale`;
- `superseded`.

A failed or uncertain sidecar should remain visible to tooling without being ranked as authoritative evidence.

## 12. Rollout

### Phase 1: ADR pilot

- define ADR eligibility contract;
- add structured evaluation output;
- create ADR schema validation;
- add a manual reconciliation command;
- produce baseline coverage metrics.

### Phase 2: Diagram conformance

- define allowed diagram kinds;
- validate Mermaid syntax;
- add duplicate detection;
- compare Codex, Claude, and any local provider against the same fixtures.

### Phase 3: Derived edge hardening

- validate controlled relationship types;
- verify reverse-edge consistency;
- detect cycles and contradictory replacement chains.

### Phase 4: General sidecar framework

- shared manifest;
- shared lifecycle states;
- provider adapter contract;
- scheduled or event-driven reconciliation through existing Memory Seed workflows.

## 13. Acceptance criteria

- No required sidecar evaluation can be silently omitted.
- Every enabled sidecar kind has an eligibility contract.
- Every generated sidecar passes a deterministic schema check.
- `not_applicable`, `uncertain`, and `failed` are distinct states.
- A reconciliation command identifies historical gaps.
- Coverage can be compared across providers.
- Provider differences affect output quality but not minimum workflow compliance.
