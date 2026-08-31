---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_entry_id_scheme
title: Deterministic 80-bit mse_ ids; legacy ms- never rewritten
topics:
  - schema
created_at: 2026-08-06T17:04:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Deterministic 80-bit mse_ ids; legacy ms- never rewritten

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `ms-a4282580:d2`

### Decision

New generated entry IDs are `mse_` plus 80 bits in 16 lower-case Base32 characters; legacy `ms-` IDs remain valid forever and are never rewritten.

### Reason

80 bits is the practical middle ground for collision risk at team scale while staying materially shorter than a 128-bit visible id.

### Impact

Converged from the control-file founding onto the decision that set the scheme.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:04:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    }
  ],
  "event_id": "adre_978f46af066ea2aa92c4",
  "founding_quote": "Entry-ID widening + MCP metadata filters (shipped 2.12.0): new generated session `entry_id` values use deterministic 80-bit `mse_` IDs while legacy `ms-` IDs remain valid and are never rewritten.",
  "founding_source": ".memory-seed/index.md#L149",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

New generated session entry_id values use deterministic 80-bit mse_ IDs encoded in 16 lower-case Base32 characters. Legacy ms- IDs remain valid forever and are never rewritten.

#### Reason

80 bits is the practical middle ground for collision risk at team scale, materially shorter than 128-bit visible IDs, and negligible collision risk for plausible Memory Seed corpora. Preserving legacy IDs maintains append-only immutability and backward compatibility.

#### Impact

Evolved in mse_77cn2v0rg9na3w0v:d1 where generate_session_entry_id() was implemented to emit deterministic mse_ IDs using SHA-256 and Crockford/Base32 alphabet.

### revision-accepted - 2026-08-06T21:12:00Z

```json
{
  "event_id": "adre_c5d98e19a6d25d5357ee",
  "founding_source": ".memory-seed/index.md#L149",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L149.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L149 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-07T05:00:00Z

```json
{
  "decision_ref": "ms-a4282580:d2",
  "event_id": "adre_a156a986253e675b6184",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Decision

New generated entry IDs are `mse_` plus 80 bits in 16 lower-case Base32 characters; legacy `ms-` IDs remain valid forever and are never rewritten.

#### Reason

80 bits is the practical middle ground for collision risk at team scale while staying materially shorter than a 128-bit visible id.

#### Impact

Converged from the control-file founding onto the decision that set the scheme.

### revision-accepted - 2026-08-07T05:10:00Z

```json
{
  "decision_ref": "ms-a4282580:d2",
  "event_id": "adre_6bf3e00c5eb21aa9deed",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L149",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Decision

Accept ms-a4282580:d2.

#### Reason

Approved by JNL 2026-08-07 from the screening shortlist.

#### Impact

ms-a4282580:d2 becomes the authoritative decision; later contrary evidence requires a successor revision.
