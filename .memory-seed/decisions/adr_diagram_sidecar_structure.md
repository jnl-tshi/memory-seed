---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_diagram_sidecar_structure
title: "Diagram sidecars: one dated file per day, keyed by entry, deterministically validated"
topics:
  - mermaid
  - session-logging
  - documentation
created_at: 2026-08-08T03:01:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Diagram sidecars: one dated file per day, keyed by entry, deterministically validated

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Diagram sidecars are one dated file per day rather than one file per entry, with multiple diagram blocks appended and each block keyed by `entry_id` inside. Validation is deterministic and lives in the single sidecar validator, covering frontmatter integrity, block shape and orphan references.

### Why

One file per entry multiplied files without adding information and made a day's diagrams impossible to browse together; keying the block by entry_id inside the file keeps the association exact while letting the filesystem mirror the session-log convention. Deterministic validation in one validator is what stops the sidecar family drifting from the rules the other families already follow.

### How it evolved

The sidecar family moved from per-entry files to one dated file per day with entry-keyed blocks, and its validation was folded into the single sidecar validator rather than kept as a separate check.

### Constitution

- `constitution:v1#single-source` (governing)
- `constitution:v1#markdown-authority` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_0vbj4zdcc11s3ggj:d1",
  "event_id": "adre_0dff99d938c286da0031",
  "source": "derived",
  "supporting_decisions": [
    "mse_m677wfhvq7s8b1x8:d1"
  ],
  "update_entry_id": "mse_0vbj4zdcc11s3ggj"
}
```

#### Decision

Diagram sidecars are one dated file per day rather than one file per entry, with multiple diagram blocks appended and each block keyed by `entry_id` inside. Validation is deterministic and lives in the single sidecar validator, covering frontmatter integrity, block shape and orphan references.

#### Why

One file per entry multiplied files without adding information and made a day's diagrams impossible to browse together; keying the block by entry_id inside the file keeps the association exact while letting the filesystem mirror the session-log convention. Deterministic validation in one validator is what stops the sidecar family drifting from the rules the other families already follow.

#### Evolution

The sidecar family moved from per-entry files to one dated file per day with entry-keyed blocks, and its validation was folded into the single sidecar validator rather than kept as a separate check.
