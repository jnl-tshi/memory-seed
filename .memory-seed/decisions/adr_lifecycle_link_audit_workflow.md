---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_lifecycle_link_audit_workflow
title: Link audit writes inert stubs; only an approval turns one into an edge
topics:
  - lifecycle-edges
  - related-entries
  - session-fuse
created_at: 2026-08-08T03:02:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Link audit writes inert stubs; only an approval turns one into an edge

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_cp5brtvkwgkt8xav:d1`

### Decision

Link-audit candidates are classified by the two-run link swarm and written automatically as live, retractable source: derived edges with confidence and a grounding quote; replaces/refines only when both runs agree; entries judged all-none record edge_status: not_applicable. Human approval is replaced by optional human verification (memory-seed link verify), which raises an edge to full weight. Machine edges never move an ADR head.

### Reason

JNL decided on 2026-09-25 that routine link classification should not wait for a human (47 stubs had accumulated). Two-run agreement and ADR-head protection carry the measured lessons: single-run refines agreement near a coin flip, and a machine edge once moved an ADR onto an unrelated concern.

### Impact

ESR's lifecycle-link gaps are cleared by link batch-plan --open-stubs, two swarm runs and link batch-apply; retrieval scales a machine replaces by its confidence; open classify_pending stubs should trend to zero.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:02:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#evidence-first",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#link-corrections",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_63qcaab119xmyx0b:d2",
  "event_id": "adre_8990c6e4b4a4c141d677",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_jg33a730vpr4085a:d1"
  ],
  "update_entry_id": "mse_63qcaab119xmyx0b"
}
```

#### Decision

The link audit writes classified but INERT stubs for candidate lifecycle edges. A stub is never a live edge: it becomes one only through an explicit approval, and an entry whose candidates were all judged unrelated records that verdict rather than being left silently unexamined.

#### Reason

A sweep that wrote live edges directly would let a mechanical candidate generator author lineage, which is the one thing the edge grammar reserves for a deliberate act. Keeping the stub inert separates 'this pair might be related' from 'this pair IS related' - the first is cheap and can be wrong, the second is a claim the graph carries. Recording the negative verdict matters for the same reason: 'looked and found nothing' and 'never looked' are different states.

#### Impact

The audit gained stub creation for missed dates and flagged upgrade candidates for review, with conversion to a live edge gated behind explicit approval rather than following automatically from detection.

### revision-rejected - 2026-08-08T23:11:00Z

```json
{
  "decision_ref": "mse_63qcaab119xmyx0b:d2",
  "event_id": "adre_c643bd1d1e42e563480f",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_63qcaab119xmyx0b:d2.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_63qcaab119xmyx0b:d2 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:11:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#evidence-first",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#link-corrections",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_63qcaab119xmyx0b:d2",
  "event_id": "adre_2df4b1eb1effb1f6b640",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_jg33a730vpr4085a:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

The link audit writes inert stubs with machine-detected candidate edges, classified but not yet live. Only explicit human approval converts a stub into an actual edge. Negative verdicts—entries whose candidates were all judged unrelated—are recorded rather than left unexamined.

#### Reason

A mechanical candidate generator should not author lineage; that remains a deliberate human act. Keeping stubs inert separates the cheap claim "might be related" from the graph claim "IS related." Recording negative verdicts distinguishes "looked and found nothing" from "never looked," both important states for maintenance and completeness.

#### Impact

Proposed the lifecycle-link authoring assist scaffold with inert stubs containing entry_id and commented candidate evidence that authors would resolve into real edges (mse_jg33a730vpr4085a:d1). Implemented and executed the audit for two dates, creating inert stub files with classified candidates and flagging five cases where the evolves litmus read clearly, withholding approval conversion pending user decision (mse_63qcaab119xmyx0b:d2).

### revision-accepted - 2026-08-08T23:11:40Z

```json
{
  "decision_ref": "mse_63qcaab119xmyx0b:d2",
  "event_id": "adre_3851e492e76608cb2d9c",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_63qcaab119xmyx0b:d2.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_63qcaab119xmyx0b:d2 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-09-25T21:09:56Z

```json
{
  "decision_ref": "mse_s8703seebha20g85:d1",
  "event_id": "adre_1a2414d3a62483fc5d6c",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_63qcaab119xmyx0b:d2",
      "relation_assertion": "link:mse_s8703seebha20g85:d1:evolves:mse_63qcaab119xmyx0b:d2"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_cp5brtvkwgkt8xav"
}
```

#### Decision

Approved classify_pending stubs are resolved by appending live evolves edges in a new sidecar block, never by editing the stub in place.

#### Reason

Recorded as the chain's intermediate form (refines mse_63qcaab119xmyx0b:d2 on 2026-07-29) so the 2026-09-25 revision descends from the accepted head; it is superseded in the same review by the automatic-classification revision.

#### Impact

Stub resolution is append-only; the fuse imports new blocks but not in-place stub edits.

### revision-proposed - 2026-09-25T21:09:57Z

```json
{
  "decision_ref": "mse_cp5brtvkwgkt8xav:d1",
  "event_id": "adre_14330111c563b084c11f",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_s8703seebha20g85:d1",
      "relation_assertion": "link:mse_cp5brtvkwgkt8xav:d1:evolves:mse_s8703seebha20g85:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_cp5brtvkwgkt8xav"
}
```

#### Decision

Link-audit candidates are classified by the two-run link swarm and written automatically as live, retractable source: derived edges with confidence and a grounding quote; replaces/refines only when both runs agree; entries judged all-none record edge_status: not_applicable. Human approval is replaced by optional human verification (memory-seed link verify), which raises an edge to full weight. Machine edges never move an ADR head.

#### Reason

JNL decided on 2026-09-25 that routine link classification should not wait for a human (47 stubs had accumulated). Two-run agreement and ADR-head protection carry the measured lessons: single-run refines agreement near a coin flip, and a machine edge once moved an ADR onto an unrelated concern.

#### Impact

ESR's lifecycle-link gaps are cleared by link batch-plan --open-stubs, two swarm runs and link batch-apply; retrieval scales a machine replaces by its confidence; open classify_pending stubs should trend to zero.

### revision-accepted - 2026-09-25T21:09:58Z

```json
{
  "decision_ref": "mse_cp5brtvkwgkt8xav:d1",
  "event_id": "adre_3a6bc827361223939cfd",
  "expected_authoritative_decision": "mse_63qcaab119xmyx0b:d2",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_cp5brtvkwgkt8xav"
}
```

#### Decision

Accept mse_cp5brtvkwgkt8xav:d1.

#### Reason

JNL explicitly approved this revision on 2026-09-25 after reviewing its Decision, Reason and Evidence.

#### Impact

mse_cp5brtvkwgkt8xav:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.

### revision-rejected - 2026-09-25T21:10:27Z

```json
{
  "decision_ref": "mse_s8703seebha20g85:d1",
  "event_id": "adre_e5d010507c5d9c65dc2c",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_cp5brtvkwgkt8xav"
}
```

#### Decision

Reject mse_s8703seebha20g85:d1.

#### Reason

Intermediate chain form recorded only for lineage; superseded in the same review by the accepted automatic-classification revision.

#### Impact

mse_s8703seebha20g85:d1 is not adopted and the current authoritative decision remains unchanged.
