---
title: "Proposal: Sidecar Lens Architecture"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded: "2026-07-20"
superseded_by: "../1_Inbox/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Sidecar Lens Architecture

**Status:** Proposed  
**Decision class:** Core architecture  
**Applies to:** Timeline entries, ADR sidecars, diagram sidecars, derived edges, future knowledge lenses, Memory Trace retrieval and display

## 1. Problem

The canonical Memory Seed timeline records what happened, but a chronological record is not always the most efficient representation for a particular task.

Humans and agents repeatedly ask different questions of the same evidence:

- What happened?
- What architectural decision was made?
- What does the system look like?
- What did this idea evolve from?
- What later replaced it?
- Why does the current implementation exist?
- What remains unresolved?
- What was validated?
- What assumption is this decision relying on?

Trying to encode every answer directly into the canonical entry would make entries noisy and difficult to author. Leaving every answer implicit forces agents to repeat the same inference whenever the question recurs.

## 2. Proposal

Adopt **lens** as the general architectural concept and **sidecar** as one storage mechanism for lenses.

A lens is a task-oriented, high-signal representation derived from canonical timeline evidence. It is introduced only when it removes a repeated inference or materially reduces decision effort.

The canonical timeline remains the source of truth. Lenses do not replace it; they provide alternate routes through it.

## 3. Existing lenses

### 3.1 Timeline lens

**Question answered:** What happened, and in what order?

**Primary beneficiaries:** Humans and agents  
**Representation:** Canonical entries  
**Authority:** Canonical

### 3.2 ADR lens

**Question answered:** Which decisions materially shaped or will shape the system architecture?

**Primary beneficiaries:** Humans and agents  
**Representation:** ADR sidecars linked to supporting entries  
**Authority:** Derived until reviewed or promoted

The ADR should identify the specific decision it represents. A single entry may support more than one decision, and references to that entry must not ambiguously imply that the entire entry is the ADR.

### 3.3 Diagram lens

**Question answered:** What does the relevant structure, flow, state, or relationship look like?

**Primary beneficiary:** Human review, with secondary agent value  
**Representation:** Mermaid sidecar initially, with other formats permitted where they add unique value  
**Authority:** Derived visual representation

### 3.4 Relationship lens

**Question answered:** Where did this idea come from, how did it evolve, and what later replaced it?

**Primary beneficiaries:** Agents and Memory Trace navigation  
**Representation:** Derived edge sidecar  
**Authority:** Derived

Examples include:

- `evolved-by`;
- `superseded-by`;
- `replaced-by`;
- reverse relationships corresponding to canonical forward links.

This lens prevents a highly ranked but outdated entry from being treated as current without inspecting its successors and provenance.

## 4. Metadata versus sidecar decision rule

### Put information in entry metadata when it is:

- known at write time;
- intentionally declared by the author or acting agent;
- compact enough not to overload the entry;
- useful for routine filtering or retrieval;
- expected to be stable and authoritative.

Examples:

- timestamp;
- author;
- branch;
- topics;
- intent;
- explicitly declared `evolves` relationship.

### Put information in a sidecar when it is:

- inferred or generated from existing evidence;
- an aggregate over multiple entries;
- a reverse or derived relationship;
- an alternate representation such as a diagram;
- likely to be added or corrected retroactively;
- expensive or distracting to place in every entry;
- provider- or transformation-dependent.

Examples:

- ADR extraction;
- diagram generation;
- derived reverse edges;
- assumption extraction;
- unresolved tension extraction;
- question index;
- branch-level synthesis.

### Use a computed view when it is:

- deterministically obtainable from metadata or sidecars;
- likely to change as new entries arrive;
- not itself a durable authored artefact.

Examples:

- branch lifecycle progress;
- missing validation;
- current decision lineage;
- sidecar coverage;
- unresolved questions by topic.

## 5. Representation and transformation separation

The architecture should distinguish what exists from how it was produced.

### Representations

- canonical timeline entry;
- ADR sidecar;
- diagram sidecar;
- relationship sidecar;
- assumption sidecar;
- question sidecar.

### Transformations

- classify ADR eligibility;
- generate an ADR;
- derive reverse relationships;
- render a Mermaid diagram;
- reconcile missing sidecars;
- validate sidecar schema;
- promote derived information;
- deprecate or supersede a sidecar.

This distinction permits transformations to evolve without changing the conceptual representation. For example, a better ADR extractor can replace the current extractor while ADR sidecars retain a stable schema.

## 6. Sidecar contract

Every sidecar type should define:

```yaml
sidecar:
  schema_version: "1"
  kind: adr
  sidecar_id: adr-...
  source_entries:
    - entry-id
  subject:
    decision_id: decision-id
  status: generated
  created_at: 2026-07-18T00:00:00Z
  generator:
    tool: memory-seed
    version: "..."
    provider: "..."
    model: "..."
    policy_version: "..."
  confidence: 0.88
  evidence:
    - entry_id: entry-id
      anchors:
        - decision-heading
  review:
    state: unreviewed
  supersedes: []
```

The exact schema may vary by sidecar, but the following concepts should be common:

- stable identity;
- sidecar kind;
- schema version;
- source entries;
- subject identity where an entry contains multiple decisions;
- generation provenance;
- confidence or uncertainty where applicable;
- review or promotion state;
- evidence anchors;
- supersession.

## 7. Lens admission criteria

A candidate lens should not be adopted merely because it can be extracted.

It should meet most of the following criteria:

1. **Recurring question:** The same question is repeatedly asked.
2. **Repeated inference:** Humans or agents repeatedly reconstruct the answer from prose.
3. **Decision effect:** The answer can alter, constrain, or support future work.
4. **Compression value:** The lens materially reduces cognitive, navigation, or token cost.
5. **Stable schema:** The output can be represented with a bounded contract.
6. **Traceability:** The result can point back to supporting evidence.
7. **Coverage testability:** Missing or invalid instances can be detected.
8. **Acceptable maintenance:** Regeneration and reconciliation costs are proportionate.
9. **Distinct value:** The lens is not a duplicate of metadata or an existing sidecar.

## 8. Retrieval model

Lenses should complement, not replace, existing retrieval signals.

A retrieval request may use:

- lexical matching;
- semantic similarity;
- topic neighbourhoods;
- recency;
- importance;
- entry intent;
- relationship traversal;
- sidecar kind;
- decision state;
- provenance and supersession.

A typical decision-oriented retrieval flow could be:

1. Retrieve candidate canonical entries using lexical, semantic, topic, recency, and importance signals.
2. Expand candidates through derived provenance and successor edges.
3. Prefer current, non-superseded decision representations where applicable.
4. Retrieve ADR or other relevant sidecars.
5. return the compressed representation with direct evidence links.
6. Permit expansion back to the canonical timeline.

## 9. Human and agent presentation

Memory Trace should clearly distinguish:

- canonical content;
- generated sidecars;
- reviewed or promoted sidecars;
- confidence and unresolved uncertainty;
- outdated or superseded sidecars;
- source entries.

The user should be able to move in both directions:

- timeline entry → available lenses;
- lens → exact supporting entries and anchors.

## 10. Risks

### Sidecar proliferation

Mitigation: require the lens admission criteria and pilot new lenses before making them core.

### Divergence from the timeline

Mitigation: evidence links, regeneration, schema validation, supersession, and visible review state.

### Ambiguous ADR references

Mitigation: assign decision-level identities within sidecars rather than treating an entire source entry as a single decision.

### Generated artefacts becoming falsely authoritative

Mitigation: explicit `generated`, `reviewed`, and `promoted` states.

### Retrieval becoming overly complex

Mitigation: keep the canonical retrieval path available and introduce lens-aware ranking incrementally.

## 11. Acceptance criteria

- “Lens” is documented as the general concept.
- Metadata, sidecar, and computed-view decision rules are adopted.
- Current ADR, diagram, and relationship sidecars use a common provenance model.
- Each sidecar links to precise source entries and, where possible, deterministic anchors.
- ADR sidecars distinguish individual decisions from source entries.
- New lens proposals must satisfy the admission criteria.
