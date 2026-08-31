---
format: memory-seed-adr/1
schema_version: 1
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

Authoritative decision: `mse_63qcaab119xmyx0b:d2`

### Decision

The link audit writes inert stubs with machine-detected candidate edges, classified but not yet live. Only explicit human approval converts a stub into an actual edge. Negative verdicts—entries whose candidates were all judged unrelated—are recorded rather than left unexamined.

### Why

A mechanical candidate generator should not author lineage; that remains a deliberate human act. Keeping stubs inert separates the cheap claim "might be related" from the graph claim "IS related." Recording negative verdicts distinguishes "looked and found nothing" from "never looked," both important states for maintenance and completeness.

### How it evolved

Proposed the lifecycle-link authoring assist scaffold with inert stubs containing entry_id and commented candidate evidence that authors would resolve into real edges (mse_jg33a730vpr4085a:d1). Implemented and executed the audit for two dates, creating inert stub files with classified candidates and flagging five cases where the evolves litmus read clearly, withholding approval conversion pending user decision (mse_63qcaab119xmyx0b:d2).

### Constitution

- `constitution:v1#evidence-first` (governing)
- `constitution:v1#link-corrections` (supporting)

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
  "source": "derived",
  "supporting_decisions": [
    "mse_jg33a730vpr4085a:d1"
  ],
  "update_entry_id": "mse_63qcaab119xmyx0b"
}
```

#### Decision

The link audit writes classified but INERT stubs for candidate lifecycle edges. A stub is never a live edge: it becomes one only through an explicit approval, and an entry whose candidates were all judged unrelated records that verdict rather than being left silently unexamined.

#### Why

A sweep that wrote live edges directly would let a mechanical candidate generator author lineage, which is the one thing the edge grammar reserves for a deliberate act. Keeping the stub inert separates 'this pair might be related' from 'this pair IS related' - the first is cheap and can be wrong, the second is a claim the graph carries. Recording the negative verdict matters for the same reason: 'looked and found nothing' and 'never looked' are different states.

#### Evolution

The audit gained stub creation for missed dates and flagged upgrade candidates for review, with conversion to a live edge gated behind explicit approval rather than following automatically from detection.

### revision-rejected - 2026-08-08T23:11:00Z

```json
{
  "decision_ref": "mse_63qcaab119xmyx0b:d2",
  "event_id": "adre_c643bd1d1e42e563480f",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

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
  "source": "derived",
  "supporting_decisions": [
    "mse_jg33a730vpr4085a:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

The link audit writes inert stubs with machine-detected candidate edges, classified but not yet live. Only explicit human approval converts a stub into an actual edge. Negative verdicts—entries whose candidates were all judged unrelated—are recorded rather than left unexamined.

#### Why

A mechanical candidate generator should not author lineage; that remains a deliberate human act. Keeping stubs inert separates the cheap claim "might be related" from the graph claim "IS related." Recording negative verdicts distinguishes "looked and found nothing" from "never looked," both important states for maintenance and completeness.

#### Evolution

Proposed the lifecycle-link authoring assist scaffold with inert stubs containing entry_id and commented candidate evidence that authors would resolve into real edges (mse_jg33a730vpr4085a:d1). Implemented and executed the audit for two dates, creating inert stub files with classified candidates and flagging five cases where the evolves litmus read clearly, withholding approval conversion pending user decision (mse_63qcaab119xmyx0b:d2).

### revision-accepted - 2026-08-08T23:11:40Z

```json
{
  "decision_ref": "mse_63qcaab119xmyx0b:d2",
  "event_id": "adre_3851e492e76608cb2d9c",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```
