---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_windows_encoding_policy
title: Encoding policy is owned by Memory Seed, with explicit check and repair tooling
topics:
  - windows-encoding
  - seed-core
created_at: 2026-08-08T03:07:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Encoding policy is owned by Memory Seed, with explicit check and repair tooling

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Encoding policy - UTF-8, LF, NFC normalisation - is owned by Memory Seed and never duplicated in Memory Trace. Explicit check and repair tooling validates files and reports normalisations safely; invalid UTF-8 and likely mojibake stay blocked for manual review rather than being repaired automatically.

### Why

Memory Trace already depends on the core package, so one owner keeps UTF-8/LF/NFC policy, exclusions and backup behaviour consistent rather than letting two copies drift. Automatic repair is rejected because the intended source characters cannot be inferred from corrupted bytes, so a repair would be a guess written as a correction.

### How it evolved

2026-07-07 implemented the encoding policy; 2026-07-08 added the encoding check slice, then confirmed Memory Seed as the single owner and added explicit check/repair tooling.

### Constitution

- `constitution:v1#single-source` (governing)
- `constitution:v1#prove-automation` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:07:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#prove-automation",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_74ddxsena9nj2afk:d1",
  "event_id": "adre_2a5a58f9b45b74563687",
  "source": "derived",
  "supporting_decisions": [
    "mse_76r59d5yxcqy0kb8:d2",
    "mse_2rvggg1jy6y4m1g3:d2"
  ],
  "update_entry_id": "mse_74ddxsena9nj2afk"
}
```

#### Decision

Encoding policy - UTF-8, LF, NFC normalisation - is owned by Memory Seed and never duplicated in Memory Trace. Explicit check and repair tooling validates files and reports normalisations safely; invalid UTF-8 and likely mojibake stay blocked for manual review rather than being repaired automatically.

#### Why

Memory Trace already depends on the core package, so one owner keeps UTF-8/LF/NFC policy, exclusions and backup behaviour consistent rather than letting two copies drift. Automatic repair is rejected because the intended source characters cannot be inferred from corrupted bytes, so a repair would be a guess written as a correction.

#### Evolution

2026-07-07 implemented the encoding policy; 2026-07-08 added the encoding check slice, then confirmed Memory Seed as the single owner and added explicit check/repair tooling.
