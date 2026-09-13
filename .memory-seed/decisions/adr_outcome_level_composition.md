---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_outcome_level_composition
title: Outcome-level operations compose deterministic continuations
topics:
  - mcp-tools
  - retrieval
  - control-plane
created_at: 2026-09-05T22:54:17Z
user_initials: JNL
agent_type: codex
source: write-time
---

# Outcome-level operations compose deterministic continuations

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_d1h4mf4z40epm8jz:d2`

### Decision

Shared core operations automatically compose mechanically determined continuations within declared scope and budget, while stopping at genuine judgment, authority, or risk boundaries. CLI and MCP expose the same outcome and retain full validation, provenance, omissions, and stopping reasons.

### Reason

Manual chaining makes agents spend tokens and attention on transitions that validated code can determine, increases skipped-step risk, and makes bypassing Memory Seed easier than using it correctly.

### Impact

Outcome-level operations should reduce agent round trips and token input without reducing evidence completeness, authority fidelity, validation coverage, or human control; the first proof slice is search plus bounded exact-chunk hydration.

### Constitution

- `constitution:v1#path-of-least-resistance` (governing)
- `constitution:v1#minimal-context` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-09-05T22:54:17Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#path-of-least-resistance",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#minimal-context",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_d1h4mf4z40epm8jz:d2",
  "event_id": "adre_d941a90cb7a85d35f749",
  "impact_provenance": "preserved",
  "source": "write-time",
  "supporting_decisions": [
    "mse_d1h4mf4z40epm8jz:d1"
  ],
  "update_entry_id": "mse_d1h4mf4z40epm8jz"
}
```

#### Decision

Shared core operations automatically compose mechanically determined continuations within declared scope and budget, while stopping at genuine judgment, authority, or risk boundaries. CLI and MCP expose the same outcome and retain full validation, provenance, omissions, and stopping reasons.

#### Reason

Manual chaining makes agents spend tokens and attention on transitions that validated code can determine, increases skipped-step risk, and makes bypassing Memory Seed easier than using it correctly.

#### Impact

Outcome-level operations should reduce agent round trips and token input without reducing evidence completeness, authority fidelity, validation coverage, or human control; the first proof slice is search plus bounded exact-chunk hydration.

### revision-accepted - 2026-09-05T22:54:38Z

```json
{
  "decision_ref": "mse_d1h4mf4z40epm8jz:d2",
  "event_id": "adre_bfdb3d69fe5212e70110",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_d1h4mf4z40epm8jz"
}
```

#### Decision

Accept mse_d1h4mf4z40epm8jz:d2.

#### Reason

JNL ratified the permanent path-of-least-resistance principle and its deterministic-versus-judgment boundary; Constitution v1.11 now governs this operational concern.

#### Impact

mse_d1h4mf4z40epm8jz:d2 becomes the authoritative decision; later contrary evidence must create a successor revision.
