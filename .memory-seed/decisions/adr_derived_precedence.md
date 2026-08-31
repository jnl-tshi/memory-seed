---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_derived_precedence
title: Derived never implicitly overrides write-time
topics:
  - control-plane
created_at: 2026-08-06T19:05:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Derived never implicitly overrides write-time

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_dqwvb8gxnn88ch3b:d1`

### Decision

Sidecar precedence across families is source rank first, then recency within a source class. A `derived` block may never implicitly override a `write-time` block on the same subject—it may only fill a gap where no write-time value exists. An explicit override is possible but requires an explicit `retracts:` naming the block it supersedes, reviewed by a human before writing. Provenance is recorded as first-hand versus reconstructed, not human versus machine.

### Reason

Once write-time values live in the sidecar, a most-recent-wins sort orders first-hand and reconstructed blocks against each other, contradicting Constitution which holds them not equal evidence. A sweep appending later would supersede a first-hand value by recency alone, contradicting the sweep's stated purpose: 'for items which did not receive them at write time.' The rule's two halves preserve that reconstructed values never displace first-hand ones silently. Human review is correct because write-time agents can be wrong, but the burden sits on the reconstructed side to state what it retracts.

### Impact

The initial decision established precedence as source rank then recency, with the core rule that derived never implicitly supersedes write-time. A subsequent correction added the second half, permitting explicit override through a named `retracts:` field reviewed by a human, recognizing that first-hand values can be wrong while maintaining that silent displacement is not allowed.

### Constitution

- `constitution:v1#provenance` (governing)
- `constitution:v1#append-only` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T19:05:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#provenance",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "event_id": "adre_c01b6c6318447dbe1e2f",
  "founding_quote": "a `derived` block may never *implicitly* override a `write-time` block on recency alone",
  "founding_source": ".memory-seed/policy.md#L44",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_dqwvb8gxnn88ch3b:d1",
    "mse_x1ha2e26md3q83zv:d1"
  ]
}
```

#### Decision

Sidecar precedence across families is source rank first, then recency. A `derived` block may never implicitly override a `write-time` block on the same subject - it may only fill a gap where no write-time value exists. An explicit override is possible but requires a human-reviewed `retracts:` naming the block it supersedes. Within a single source class most-recent-wins is unchanged. Provenance is recorded as first-hand versus reconstructed, not human versus machine.

#### Reason

Once write-time values live in sidecars, plain most-recent-wins would let a later sweep supersede a first-hand value merely by being newer, contradicting the ratified position that the two are not equal evidence. Half the rule alone would make write-time values permanently uncorrectable, so the reviewed retraction keeps a wrong first-hand value fixable while guaranteeing a reconstructed value never displaces a first-hand one silently. Approving a sweep batch was rejected as approval of a specific displacement.

#### Impact

Closed 2026-07-26 as a precedence hole in the accepted consolidation proposal, where source was made to outrank recency, then corrected hours later the same day to add the human-reviewed `retracts:` override so first-hand values stay correctable.

### revision-accepted - 2026-08-06T21:06:00Z

```json
{
  "event_id": "adre_56f4bf8804755f13fe2f",
  "founding_source": ".memory-seed/policy.md#L44",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/policy.md#L44.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/policy.md#L44 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:31:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#provenance",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_x1ha2e26md3q83zv:d1",
  "event_id": "adre_63cef7fc22d56c57e124",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Sidecar precedence across families is source rank first, then recency. A `derived` block may never implicitly override a `write-time` block on the same subject - it may only fill a gap where no write-time value exists. An explicit override is possible but requires a human-reviewed `retracts:` naming the block it supersedes. Within a single source class most-recent-wins is unchanged. Provenance is recorded as first-hand versus reconstructed, not human versus machine.

#### Reason

Rests on the session decision that instituted it: "A `derived` block may **never** supersede a `write-time` block for the same subject" (mse_x1ha2e26md3q83zv:d1). Explicitly sets the precedence rule preventing derived blocks from overriding write-time values.

#### Impact

Founded from .memory-seed/policy.md#L44; this revision moves the concern off that control-file line onto mse_x1ha2e26md3q83zv:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:26:00Z

```json
{
  "decision_ref": "mse_x1ha2e26md3q83zv:d1",
  "event_id": "adre_271b1bb2ec153e708e2c",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_x1ha2e26md3q83zv:d1.

#### Reason

Wording retired and the anchor moved. This revision rested on mse_x1ha2e26md3q83zv:d1, but mse_dqwvb8gxnn88ch3b:d1 is a later decision in the same chain that had already moved the concern past it. A shift in the most recent authoritative decision triggers a regenerated summary, so both land together.

#### Impact

mse_x1ha2e26md3q83zv:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:26:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#provenance",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_dqwvb8gxnn88ch3b:d1",
  "event_id": "adre_83fcf7806f01c462143c",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_x1ha2e26md3q83zv:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Sidecar precedence across families is source rank first, then recency within a source class. A `derived` block may never implicitly override a `write-time` block on the same subject—it may only fill a gap where no write-time value exists. An explicit override is possible but requires an explicit `retracts:` naming the block it supersedes, reviewed by a human before writing. Provenance is recorded as first-hand versus reconstructed, not human versus machine.

#### Reason

Once write-time values live in the sidecar, a most-recent-wins sort orders first-hand and reconstructed blocks against each other, contradicting Constitution which holds them not equal evidence. A sweep appending later would supersede a first-hand value by recency alone, contradicting the sweep's stated purpose: 'for items which did not receive them at write time.' The rule's two halves preserve that reconstructed values never displace first-hand ones silently. Human review is correct because write-time agents can be wrong, but the burden sits on the reconstructed side to state what it retracts.

#### Impact

The initial decision established precedence as source rank then recency, with the core rule that derived never implicitly supersedes write-time. A subsequent correction added the second half, permitting explicit override through a named `retracts:` field reviewed by a human, recognizing that first-hand values can be wrong while maintaining that silent displacement is not allowed.

### revision-accepted - 2026-08-08T23:26:40Z

```json
{
  "decision_ref": "mse_dqwvb8gxnn88ch3b:d1",
  "event_id": "adre_1e4dad771e46a151790e",
  "expected_authoritative_decision": "founding:.memory-seed/policy.md#L44",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_dqwvb8gxnn88ch3b:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_dqwvb8gxnn88ch3b:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
