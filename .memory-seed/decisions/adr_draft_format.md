---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_draft_format
title: DRAFT single-decision baseline; D/R mandatory; numbered decisions canonical
topics:
  - session-logging
  - schema
created_at: 2026-08-06T17:05:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# DRAFT single-decision baseline; D/R mandatory; numbered decisions canonical

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L143`

### Decision

The single-decision DRAFT record is the baseline session-entry shape. D/R (Decision/Rationale) are mandatory fields; A/F/T (Alternatives/Findings/Tests) are optional. Multi-decision entries use numbered #### Dn headings as the canonical form.

### Reason

A baseline structure with mandatory decision rationale ensures every memory entry captures the core reasoning. Explicit numbering makes multi-decision entries unambiguous and discoverable.

### Impact

Founded from the control file; established as baseline in 2.4.0 per the control plane history.

### Constitution

- `constitution:v1#draft-format` (governing)

### Awaiting review

- `ms-db2d715c:d1` - The single-decision DRAFT record is the baseline session-entry shape.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:05:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#draft-format",
      "role": "governing"
    }
  ],
  "event_id": "adre_fda067eda66d13c010d7",
  "founding_quote": "The single-decision DRAFT record is the **baseline** session-entry shape (since 2.4.0); the bare summary (simpler) and multi-decision (richer) shapes are explicit routes off it. D/R are mandatory, A/F/T optional.",
  "founding_source": ".memory-seed/index.md#L143",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

The single-decision DRAFT record is the baseline session-entry shape. D/R (Decision/Rationale) are mandatory fields; A/F/T (Alternatives/Findings/Tests) are optional. Multi-decision entries use numbered #### Dn headings as the canonical form.

#### Reason

A baseline structure with mandatory decision rationale ensures every memory entry captures the core reasoning. Explicit numbering makes multi-decision entries unambiguous and discoverable.

#### Impact

Founded from the control file; established as baseline in 2.4.0 per the control plane history.

### revision-accepted - 2026-08-06T21:08:00Z

```json
{
  "event_id": "adre_8396955a0aa57e737b22",
  "founding_source": ".memory-seed/index.md#L143",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L143.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L143 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:32:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#draft-format",
      "role": "governing"
    }
  ],
  "decision_ref": "ms-db2d715c:d1",
  "event_id": "adre_57c1d50099c463b1795b",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

The single-decision DRAFT record is the baseline session-entry shape. D/R (Decision/Rationale) are mandatory fields; A/F/T (Alternatives/Findings/Tests) are optional. Multi-decision entries use numbered #### Dn headings as the canonical form.

#### Reason

Rests on the session decision that instituted it: "Use `D`, `R`, `A`, `F`, and `T` labels for decision, rationale, alternatives, files/artifacts/behaviors, and tests/validation" (ms-db2d715c:d1). Institutes the DRAFT label vocabulary that makes D/R mandatory in all decision records.

#### Impact

Founded from .memory-seed/index.md#L143; this revision moves the concern off that control-file line onto ms-db2d715c:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
