---
title: Decision sidecar envelope contract
status: draft
spec_binding: draft
parent: ../../2_Todo/write-time-sidecar-consolidation-proposal.md
---

# DecisionSidecarEnvelope v1

Status: **DRAFT — M0 contract, not implemented.**

## Constitutional fit

This contract stays within the Constitution: Markdown remains the local authoritative substrate; the
entry owns narrative and evidence; every semantic field has exactly one sidecar owner; the write is
append-only and passes identical shared-core validation through CLI and MCP. A recovery journal and a
write receipt are operational, non-authoritative state. Swarm evaluation is optional and external to
the network-free core; its canonical output is provider-independent Markdown.

## Authority

| Concern | Canonical owner |
|---|---|
| Entry identity, timestamp, narrative, rationale, evidence | Session entry |
| Area/activity attribution per decision | Topic sidecar |
| `related` / `evolves` / `replaces` meaning per decision | Link sidecar |
| Diagram source per decision | Diagram sidecar |
| ADR promotion, governing decision, and design-thread lens | ADR sidecar |
| Current project implementation | Current files and live specifications |
| Transaction journal, receipts, indexes, Trace views | Derived or tool-operational state |

An ADR's direct lineage is a curated lens, not a second lifecycle ledger. Each predecessor reference must
resolve to a link-sidecar assertion. The link sidecar alone declares whether the current decision evolves or
replaces its predecessor.

## Request shape

The existing `memory_session_append` is extended compatibly. Legacy top-level `topics`, `related_entries`,
`evolves`, and `replaces` are accepted only during migration. New writers send `decisions`.

```yaml
title: Adopt transaction-backed sidecar writes
body: |
  ### Decisions

  #### D1 - Use a composite writer

  - D: ...
  - R: ...
  - F: `memory_seed/core.py`
user_initials: JNL
agent_type: codex
decisions:
  - decision: d1
    topics:
      area: seed-core
      activity: feature-build
      source: write-time
    links:
      evolves:
        - mse_prior:d1
      evidence:
        - consulted: mse_prior
    diagrams:
      - title: Write and recovery flow
        mermaid: flowchart TD\n  A[Validate] --> B[Stage]
    adr:
      disposition: promote
      title: Composite decision-sidecar writer
      direct_predecessors:
        - decision: mse_prior:d1
          assertion: link:mse_current:d1:evolves:mse_prior:d1
```

The core derives `entry_id` and verifies that every `decision:` exists in the DRAFT body. It validates topic
vocabulary, link direction and decision grammar, Mermaid syntax, ADR eligibility/status, and every referenced
link assertion. `dry_run` returns the canonical id, exact Markdown blocks, and an artifact manifest.

## Write protocol

1. Validate the whole envelope before changing files.
2. Create a non-authoritative recovery journal containing the transaction id, rendered blocks, and target paths.
3. Append sidecar blocks in deterministic family order: topics, links, diagrams, ADR.
4. Append the entry last.
5. Verify the rendered artifacts, remove/mark the journal complete, and return a receipt.

The journal is operational recovery state, not memory authority. Recovery either finishes the exact staged
transaction or reports a conflict; it never rewrites a published block. An entry is not considered complete
until its receipt lists all requested sidecar artifacts.

## ADR design-thread lens

An ADR starts with a `current_decision` pointer and may append a transition when a newer architectural
decision becomes governing. Each transition records the prior current decision as a direct predecessor and
references the already-validated link assertion that says `evolves` or `replaces`.

```yaml
current_decision: mse_current:d1
direct_predecessors:
  - decision: mse_prior:d1
    relation_assertion: link:mse_current:d1:evolves:mse_prior:d1
```

The ADR's current pointer is authoritative *for the ADR's design thread*. It never overrides the source
entry's narrative or current project files. A write-time agent may promote a genuinely architectural decision;
a swarm may only propose ADR action and requires human approval before it writes a sidecar or transition.

## Branch fusion

Fusion is parsed-record reconciliation, never line-based Markdown merging. A source record is admissible only
when its parent entry is already on the base or accepted in the same fuse plan.

For every family, byte-identical records deduplicate. A matching identity with different content fails the
preview. New records are rebuilt by:

1. parent entry date and timestamp;
2. parent entry id;
3. decision ordinal;
4. sidecar event timestamp;
5. immutable record identity.

Files group records by their parent entry's session date. This keeps all sidecars for an entry discoverable
together even if its branch lands later. A concurrent ADR transition from the same expected current decision
is a semantic conflict and must fail rather than be ordered away.

## Swarm coverage and vendor neutrality

Coverage belongs to the sidecar type it evaluates and keys on `(entry_id, decision, sidecar_type,
schema_version)`. A sweep only considers records with no completed coverage at that key; `not_applicable` is
completed coverage, not an omission.

The canonical suggestion record stores the evidence, decision, rationale, provenance, and schema version.
Provider/model names and prices are execution telemetry only. A pluggable policy selects the least-cost model
that passed the calibration for the task class; it escalates when evidence conflicts, confidence is below the
calibrated threshold, or the decision is high consequence.

## Acceptance fixtures

M1 must implement the fixtures in `tests/fixtures/decision_sidecar_envelope_v1/` unchanged: one complete
write, two independent branch additions, a duplicate, a divergent block, a missing parent, and competing ADR
transitions. The fixture corpus is normative for writer and fuse tests.
