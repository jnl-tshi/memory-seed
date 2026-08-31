---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_edge_kinds
title: Four never-merged edge kinds, forward-only and acyclic
topics:
  - lifecycle-edges
  - graph
created_at: 2026-08-06T17:01:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Four never-merged edge kinds, forward-only and acyclic

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_0qycwt519qdggrpe:d1`

### Decision

Lifecycle edges comprise three kinds: `related` (thematic association), `supersedes` (replacement), and `evolves` (extension). Edges are forward-only and acyclic by design. Topic edges are not included in the default edge type set, though topic remains offered.

### Reason

The chain construction in the codebase groups entries by topic naturally through sorting logic, so a topic edge would assert only that nothing else carrying that tag occurred between two entries—a statement about sort order, not about the entries themselves. Since topology is already visible through node coloring and community naming, topic edges would render the same fact twice. The three core edge types capture genuine authored claims about specific entry pairs; topic membership is already represented through graph community structure.

### Impact

Established DEFAULT_GRAPH_EDGE_TYPES as `related`, `supersedes`, and `evolves` after analyzing the codebase construction. Removed topic from the default types because it duplicates information already conveyed by entry sort order and community coloring, and its presence was even suppressing legitimate edge types in pair-precedence logic.

### Constitution

- `constitution:v1#edge-kinds` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#edge-kinds",
      "role": "governing"
    }
  ],
  "event_id": "adre_f7fceb0992180d5596b9",
  "founding_quote": "Evolution edges and artifact lineage (core shipped in 2.18.0; Trace continuity completed 2026-07-15): typed `evolves:` plus read-time `evolved_by`, inverse-field and continuity validation",
  "founding_source": ".memory-seed/index.md#L171",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Lifecycle edges comprise four never-merged kinds: `replaces`, `evolves`, `related_entries`, and `evolved_by` (inverse). Edges are forward-only and acyclic by contract.

#### Reason

Four independent relationship claims deserve distinct semantic labels. Forward-only and acyclic structure ensures the edge graph is append-only and prevents cycles in artifact lineage.

#### Impact

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:10:00Z

```json
{
  "event_id": "adre_9f3c03fef3b77de88b8d",
  "founding_source": ".memory-seed/index.md#L171",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L171.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L171 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:33:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#edge-kinds",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_0qycwt519qdggrpe:d1",
  "event_id": "adre_14ff420e1e407cfd3cb8",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Lifecycle edges comprise four never-merged kinds: `replaces`, `evolves`, `related_entries`, and `evolved_by` (inverse). Edges are forward-only and acyclic by contract.

#### Reason

Rests on the session decision that instituted it: "`DEFAULT_GRAPH_EDGE_TYPES` becomes `related, supersedes, evolves`" (mse_0qycwt519qdggrpe:d1). Institutes the three core edge kinds system by defining DEFAULT_GRAPH_EDGE_TYPES.

#### Impact

Founded from .memory-seed/index.md#L171; this revision moves the concern off that control-file line onto mse_0qycwt519qdggrpe:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:05:00Z

```json
{
  "decision_ref": "mse_0qycwt519qdggrpe:d1",
  "event_id": "adre_669c525b8eba1e936734",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_0qycwt519qdggrpe:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_0qycwt519qdggrpe:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:05:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#edge-kinds",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_0qycwt519qdggrpe:d1",
  "event_id": "adre_7227a01138d6a2300a5b",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Lifecycle edges comprise three kinds: `related` (thematic association), `supersedes` (replacement), and `evolves` (extension). Edges are forward-only and acyclic by design. Topic edges are not included in the default edge type set, though topic remains offered.

#### Reason

The chain construction in the codebase groups entries by topic naturally through sorting logic, so a topic edge would assert only that nothing else carrying that tag occurred between two entries—a statement about sort order, not about the entries themselves. Since topology is already visible through node coloring and community naming, topic edges would render the same fact twice. The three core edge types capture genuine authored claims about specific entry pairs; topic membership is already represented through graph community structure.

#### Impact

Established DEFAULT_GRAPH_EDGE_TYPES as `related`, `supersedes`, and `evolves` after analyzing the codebase construction. Removed topic from the default types because it duplicates information already conveyed by entry sort order and community coloring, and its presence was even suppressing legitimate edge types in pair-precedence logic.

### revision-accepted - 2026-08-08T23:05:40Z

```json
{
  "decision_ref": "mse_0qycwt519qdggrpe:d1",
  "event_id": "adre_a7c9a40667d45a190452",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L171",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_0qycwt519qdggrpe:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_0qycwt519qdggrpe:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
