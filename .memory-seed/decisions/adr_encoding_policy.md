---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_encoding_policy
title: Encoding policy owned by Seed, never duplicated in Trace
topics:
  - control-plane
  - windows-encoding
  - seed-core
created_at: 2026-08-06T17:14:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Encoding policy owned by Seed, never duplicated in Trace

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace.

### Why

Memory Trace depends on the core package. One owner keeps UTF-8/LF/NFC policy, exclusions, and backup behavior consistent across the system.

### How it evolved

Established 2026-07-08 (mse_ejpbz4qqsbdx0hvc); encoding hardening P0 completed with explicit check/repair tooling in Seed.

### Constitution

- `constitution:v1#single-source` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:14:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "event_id": "adre_7dd8195c9f0fd1790f5a",
  "founding_quote": "Encoding policy stays owned by Memory Seed rather than being duplicated in Memory Trace, and `doctor` provides a non-fatal summary.",
  "founding_source": ".memory-seed/index.md#L183",
  "source": "derived"
}
```

#### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace.

#### Why

Memory Trace depends on the core package. One owner keeps UTF-8/LF/NFC policy, exclusions, and backup behavior consistent across the system.

#### Evolution

Established 2026-07-08 (mse_ejpbz4qqsbdx0hvc); encoding hardening P0 completed with explicit check/repair tooling in Seed.
