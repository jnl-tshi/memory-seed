---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_lifecycle_edges_live_in_sidecars
title: Lifecycle edges live only in link sidecars, declared per decision
topics:
  - lifecycle-edges
  - session-layout
created_at: 2026-08-09T11:46:45Z
user_initials: JNL
agent_type: claude
source: write-time
---

# Lifecycle edges live only in link sidecars, declared per decision

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_g01sqaac2c10ejd5:d3`

### Decision

Lifecycle links (replaces/evolves/related_entries) are authored ONLY through the decisions envelope and written to link sidecars. Entry YAML no longer accepts them; published entries keep theirs and are read forever.

### Why

A raw ref in an entry's YAML gives a human reading the Markdown nothing, and Invariant #6 already assigns lifecycle facts to narrow sidecars while entries own narrative rationale. The entry-level flags also cannot carry a per-edge 'why' or evolution type, so keeping them would leave two write surfaces of unequal strength - the parity failure Constitution 1.3 forbids.

### How it evolved

This is the first revision of this architectural concern.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-09T11:46:45Z

```json
{
  "decision_ref": "mse_g01sqaac2c10ejd5:d3",
  "event_id": "adre_45653c79fa5238ecc95f",
  "source": "write-time",
  "update_entry_id": "mse_g01sqaac2c10ejd5"
}
```

#### Decision

Lifecycle links (replaces/evolves/related_entries) are authored ONLY through the decisions envelope and written to link sidecars. Entry YAML no longer accepts them; published entries keep theirs and are read forever.

#### Why

A raw ref in an entry's YAML gives a human reading the Markdown nothing, and Invariant #6 already assigns lifecycle facts to narrow sidecars while entries own narrative rationale. The entry-level flags also cannot carry a per-edge 'why' or evolution type, so keeping them would leave two write surfaces of unequal strength - the parity failure Constitution 1.3 forbids.

#### Evolution

This is the first revision of this architectural concern.

### revision-accepted - 2026-08-09T16:53:51Z

```json
{
  "decision_ref": "mse_g01sqaac2c10ejd5:d3",
  "event_id": "adre_59133bd6b1f26a7e4910",
  "source": "write-time",
  "update_entry_id": "mse_g01sqaac2c10ejd5"
}
```

#### Reason

JNL accepted 2026-08-09: the entry-YAML closure is merged and shipped, so the ADR records standing authority rather than a pending proposal.
