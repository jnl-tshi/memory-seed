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
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L183`

### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace.

### Why

Memory Trace depends on the core package. One owner keeps UTF-8/LF/NFC policy, exclusions, and backup behavior consistent across the system.

### How it evolved

Established 2026-07-08 (mse_ejpbz4qqsbdx0hvc); encoding hardening P0 completed with explicit check/repair tooling in Seed.

### Constitution

- `constitution:v1#single-source` (governing)

### Awaiting review

- `mse_74ddxsena9nj2afk:d1` - Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in...

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

### revision-accepted - 2026-08-06T21:11:00Z

```json
{
  "event_id": "adre_d48875abf6634b606d3c",
  "founding_source": ".memory-seed/index.md#L183",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:05:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_74ddxsena9nj2afk:d1",
  "event_id": "adre_b2028e60c20f9b6161b6",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace.

#### Why

Rests on the session decision that instituted it: "Keep encoding policy in Memory Seed and add explicit check/repair tooling rather than duplicating an encoding command surface" (mse_74ddxsena9nj2afk:d1). Established Seed as the sole owner of encoding policy, preventing duplication in Trace.

#### Evolution

Founded from .memory-seed/index.md#L183; this revision moves the concern off that control-file line onto mse_74ddxsena9nj2afk:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### context-added - 2026-08-08T20:42:00Z

```json
{
  "event_id": "adre_4dadabb7727548ddf0da",
  "source": "derived",
  "supporting_decisions": [
    "mse_76r59d5yxcqy0kb8:d2",
    "mse_2rvggg1jy6y4m1g3:d2"
  ],
  "update_entry_id": "mse_cq88k8kb8k3wp1cb"
}
```

#### Reason

Carried over when adr_windows_encoding_policy was folded into this concern: both records proposed the same head, mse_74ddxsena9nj2afk:d1. Two things from that record could NOT be folded, because the same decision cannot be proposed twice on one ADR - the clause that invalid UTF-8 and likely mojibake stay blocked for manual review rather than being repaired automatically (the intended characters cannot be inferred from corrupted bytes), and constitution:v1#prove-automation as a supporting binding. The next revision of this ADR should carry both.
