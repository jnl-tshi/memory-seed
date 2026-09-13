---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `mse_0vbj4zdcc11s3ggj:d1`

### Decision

Diagram sidecars live at `.memory-seed/sessions/diagrams/YYYY-MM-DD.md` with one file per date. Each diagram is a heading block with timestamp and title, containing a YAML block with `entry_id` and one or more Mermaid blocks. Multiple diagrams logged on the same date append to the same file in ascending time order, mirroring the session-log convention. Validation is deterministic and covers frontmatter integrity, required `entry_id` presence, mermaid fence balance, filename-date matching, and orphan-reference detection.

### Reason

One file per entry multiplied files without adding information and made a day's diagrams impossible to browse together. Keying blocks by `entry_id` inside the file keeps the association exact while letting the filesystem structure mirror the session-log convention. Deterministic validation in a single validator prevents the sidecar family from drifting from rules other families follow and ensures the graph-edge contract has new artifact validation where it belongs.

### Impact

The first member established deterministic validation rules for diagram sidecars within a single validator, covering frontmatter, `entry_id` presence, fence balance, and reference resolution. The second member redesigned the file structure from per-entry_id files to one dated file per day with multiple diagram blocks, matching session-log conventions and enabling day-wide diagram browsing. Validation rules were adapted to the new structure.

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
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_m677wfhvq7s8b1x8:d1"
  ],
  "update_entry_id": "mse_0vbj4zdcc11s3ggj"
}
```

#### Decision

Diagram sidecars are one dated file per day rather than one file per entry, with multiple diagram blocks appended and each block keyed by `entry_id` inside. Validation is deterministic and lives in the single sidecar validator, covering frontmatter integrity, block shape and orphan references.

#### Reason

One file per entry multiplied files without adding information and made a day's diagrams impossible to browse together; keying the block by entry_id inside the file keeps the association exact while letting the filesystem mirror the session-log convention. Deterministic validation in one validator is what stops the sidecar family drifting from the rules the other families already follow.

#### Impact

The sidecar family moved from per-entry files to one dated file per day with entry-keyed blocks, and its validation was folded into the single sidecar validator rather than kept as a separate check.

### revision-rejected - 2026-08-08T23:02:00Z

```json
{
  "decision_ref": "mse_0vbj4zdcc11s3ggj:d1",
  "event_id": "adre_7f6f0fdf7c7a7dcdb154",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_0vbj4zdcc11s3ggj:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_0vbj4zdcc11s3ggj:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:02:20Z

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
  "event_id": "adre_d522522001e1dd414a2b",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_m677wfhvq7s8b1x8:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Diagram sidecars live at `.memory-seed/sessions/diagrams/YYYY-MM-DD.md` with one file per date. Each diagram is a heading block with timestamp and title, containing a YAML block with `entry_id` and one or more Mermaid blocks. Multiple diagrams logged on the same date append to the same file in ascending time order, mirroring the session-log convention. Validation is deterministic and covers frontmatter integrity, required `entry_id` presence, mermaid fence balance, filename-date matching, and orphan-reference detection.

#### Reason

One file per entry multiplied files without adding information and made a day's diagrams impossible to browse together. Keying blocks by `entry_id` inside the file keeps the association exact while letting the filesystem structure mirror the session-log convention. Deterministic validation in a single validator prevents the sidecar family from drifting from rules other families follow and ensures the graph-edge contract has new artifact validation where it belongs.

#### Impact

The first member established deterministic validation rules for diagram sidecars within a single validator, covering frontmatter, `entry_id` presence, fence balance, and reference resolution. The second member redesigned the file structure from per-entry_id files to one dated file per day with multiple diagram blocks, matching session-log conventions and enabling day-wide diagram browsing. Validation rules were adapted to the new structure.

### revision-accepted - 2026-08-08T23:02:40Z

```json
{
  "decision_ref": "mse_0vbj4zdcc11s3ggj:d1",
  "event_id": "adre_d70a32fed327f1a5c1ef",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_0vbj4zdcc11s3ggj:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_0vbj4zdcc11s3ggj:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
