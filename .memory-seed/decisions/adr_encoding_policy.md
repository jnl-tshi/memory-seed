---
format: memory-seed-adr/2
schema_version: 2
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

Authoritative decision: `mse_74ddxsena9nj2afk:d1`

### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace. Check tooling is in place for validation, and automatic repair of mojibake is rejected because the original characters cannot be safely inferred. Memory Trace depends on Seed and relies on its single source of truth for encoding enforcement.

### Reason

Central ownership by Seed prevents inconsistency and duplication across the system. The dependency relationship (Trace depends on Seed core) means one authoritative source suffices. Automatic repair was rejected as unsafe—when text is corrupted, the original intended characters cannot be recovered without human judgment.

### Impact

Infrastructure and central helpers were established first, adding shared utilities and repository-level configuration. The check command was then added to provide explicit validation of the UTF-8/LF/no-BOM contract. The architectural decision finalized that Seed alone owns encoding policy, with Trace relying on it rather than duplicating the surface.

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
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace.

#### Reason

Memory Trace depends on the core package. One owner keeps UTF-8/LF/NFC policy, exclusions, and backup behavior consistent across the system.

#### Impact

Established 2026-07-08 (mse_ejpbz4qqsbdx0hvc); encoding hardening P0 completed with explicit check/repair tooling in Seed.

### revision-accepted - 2026-08-06T21:11:00Z

```json
{
  "event_id": "adre_d48875abf6634b606d3c",
  "founding_source": ".memory-seed/index.md#L183",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L183.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L183 becomes the authoritative decision; later contrary evidence requires a successor revision.

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
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace.

#### Reason

Rests on the session decision that instituted it: "Keep encoding policy in Memory Seed and add explicit check/repair tooling rather than duplicating an encoding command surface" (mse_74ddxsena9nj2afk:d1). Established Seed as the sole owner of encoding policy, preventing duplication in Trace.

#### Impact

Founded from .memory-seed/index.md#L183; this revision moves the concern off that control-file line onto mse_74ddxsena9nj2afk:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### context-added - 2026-08-08T20:42:00Z

```json
{
  "event_id": "adre_4dadabb7727548ddf0da",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_76r59d5yxcqy0kb8:d2",
    "mse_2rvggg1jy6y4m1g3:d2"
  ],
  "update_entry_id": "mse_cq88k8kb8k3wp1cb"
}
```

#### Decision

Record the supplied decisions as context for this ADR.

#### Reason

Carried over when adr_windows_encoding_policy was folded into this concern: both records proposed the same head, mse_74ddxsena9nj2afk:d1. Two things from that record could NOT be folded, because the same decision cannot be proposed twice on one ADR - the clause that invalid UTF-8 and likely mojibake stay blocked for manual review rather than being repaired automatically (the intended characters cannot be inferred from corrupted bytes), and constitution:v1#prove-automation as a supporting binding. The next revision of this ADR should carry both.

#### Impact

This adds supporting context only; it does not change ADR membership, status, or authority.

### revision-rejected - 2026-08-08T23:06:00Z

```json
{
  "decision_ref": "mse_74ddxsena9nj2afk:d1",
  "event_id": "adre_3e4721007b3e91c75afc",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_74ddxsena9nj2afk:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_74ddxsena9nj2afk:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:06:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_74ddxsena9nj2afk:d1",
  "event_id": "adre_aca5ea15a5c23098dbb0",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_76r59d5yxcqy0kb8:d2",
    "mse_2rvggg1jy6y4m1g3:d2"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Encoding policy (UTF-8, LF, NFC normalization) is owned and enforced by Memory Seed core, never duplicated in Memory Trace. Check tooling is in place for validation, and automatic repair of mojibake is rejected because the original characters cannot be safely inferred. Memory Trace depends on Seed and relies on its single source of truth for encoding enforcement.

#### Reason

Central ownership by Seed prevents inconsistency and duplication across the system. The dependency relationship (Trace depends on Seed core) means one authoritative source suffices. Automatic repair was rejected as unsafe—when text is corrupted, the original intended characters cannot be recovered without human judgment.

#### Impact

Infrastructure and central helpers were established first, adding shared utilities and repository-level configuration. The check command was then added to provide explicit validation of the UTF-8/LF/no-BOM contract. The architectural decision finalized that Seed alone owns encoding policy, with Trace relying on it rather than duplicating the surface.

### revision-accepted - 2026-08-08T23:06:40Z

```json
{
  "decision_ref": "mse_74ddxsena9nj2afk:d1",
  "event_id": "adre_e60fb53fe56dfa84650e",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L183",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_74ddxsena9nj2afk:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_74ddxsena9nj2afk:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
