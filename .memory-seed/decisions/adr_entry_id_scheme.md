---
format: memory-seed-adr/1
schema_version: 1
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
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

New generated session entry_id values use deterministic 80-bit mse_ IDs encoded in 16 lower-case Base32 characters. Legacy ms- IDs remain valid forever and are never rewritten.

### Why

80 bits is the practical middle ground for collision risk at team scale, materially shorter than 128-bit visible IDs, and negligible collision risk for plausible Memory Seed corpora. Preserving legacy IDs maintains append-only immutability and backward compatibility.

### How it evolved

Evolved in mse_77cn2v0rg9na3w0v:d1 where generate_session_entry_id() was implemented to emit deterministic mse_ IDs using SHA-256 and Crockford/Base32 alphabet.

### Constitution

- `constitution:v1#append-only` (governing)

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
  "source": "derived"
}
```

#### Decision

New generated session entry_id values use deterministic 80-bit mse_ IDs encoded in 16 lower-case Base32 characters. Legacy ms- IDs remain valid forever and are never rewritten.

#### Why

80 bits is the practical middle ground for collision risk at team scale, materially shorter than 128-bit visible IDs, and negligible collision risk for plausible Memory Seed corpora. Preserving legacy IDs maintains append-only immutability and backward compatibility.

#### Evolution

Evolved in mse_77cn2v0rg9na3w0v:d1 where generate_session_entry_id() was implemented to emit deterministic mse_ IDs using SHA-256 and Crockford/Base32 alphabet.
