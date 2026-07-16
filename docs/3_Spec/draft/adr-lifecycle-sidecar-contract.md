---
title: ADR lifecycle sidecar contract
status: draft
spec_binding: memory-seed-semantic-record-and-signal-foundation-plan.md
---

# ADR Lifecycle Sidecar Contract

Status: **DRAFT - NOT IMPLEMENTED**. This contract becomes live only after the walking skeleton and validator
are accepted.

## Authority

One append-only Markdown sidecar is authoritative for an ADR's promotion, stable identity, and lifecycle.
The original and decision-update entries are authoritative for narrative rationale and evidence. Current
project files and live specs remain authoritative for what is implemented now. Registries, databases,
`current_status`, and UI views are derived.

## Shape

Candidate location: `.memory-seed/decisions/<adr_id>.md`, one file per ADR. The directory is introduced only
when this draft is adopted; this documentation pass does not create runtime state.

```markdown
---
schema_version: 1
adr_id: adr_...
source_entry_id: mse_...
source_decision: d1
title: Use SQLite for the local index
topics:
  - storage
created_at: 2026-07-16T14:20:00Z
created_by: jean
---

## Proposed - 2026-07-16T14:20:00Z

update_entry_id: mse_...

## Accepted - 2026-07-16T16:10:00Z

update_entry_id: mse_...
expected_previous_status: proposed
```

Frontmatter identity fields are fixed after creation. Corrections, topic changes, status changes, rejection,
and supersession are appended transition blocks. `current_status` is the result of replaying the single valid
transition chain and is never authored as a second state field.

CLI and MCP writers should use one shared core operation, but the file remains directly readable and editable.
A manual append is authoritative when it satisfies the same schema and validation rules; tooling must not
claim exclusive ownership of repository memory.

## Source decision identity

For new structured entries, `source_decision` resolves a deterministic decision anchor. A legacy source may
use a sidecar-owned stable decision key plus an exact heading path and optional source-text fingerprint. The
legacy entry is not edited merely to add decision metadata.

## Transition rules

- Every transition references exactly one `decision-update` entry.
- The update entry names the ADR, expected previous status, new status, author, timestamp, rationale, and
  evidence references.
- Allowed status transitions are versioned by schema. The initial set is proposed -> accepted/rejected and
  accepted -> superseded. Reconsideration requires an explicit later schema decision.
- Supersession names the replacement ADR; the inverse is computed rather than hand-maintained.
- Competing transitions from the same previous status are a conflict requiring explicit resolution, never a
  last-writer-wins merge.

## Validation

Validation must detect duplicate ADR IDs, broken source selectors, missing update entries, transition/order
errors, competing heads, unknown topics, malformed timestamps, and invalid supersession. It reports repair
guidance but does not silently mutate authored memory.

## Derived readers

Readers may derive current status, transition timelines, topic indexes, supersession chains, and Trace
projections. Every value retains source sidecar and entry references, and a full rebuild from repository
Markdown must produce equivalent output.
