---
format: memory-seed-adr/1
schema_version: 1
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

### Why

A baseline structure with mandatory decision rationale ensures every memory entry captures the core reasoning. Explicit numbering makes multi-decision entries unambiguous and discoverable.

### How it evolved

Founded from the control file; established as baseline in 2.4.0 per the control plane history.

### Constitution

- `constitution:v1#draft-format` (governing)

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
  "source": "derived"
}
```

#### Decision

The single-decision DRAFT record is the baseline session-entry shape. D/R (Decision/Rationale) are mandatory fields; A/F/T (Alternatives/Findings/Tests) are optional. Multi-decision entries use numbered #### Dn headings as the canonical form.

#### Why

A baseline structure with mandatory decision rationale ensures every memory entry captures the core reasoning. Explicit numbering makes multi-decision entries unambiguous and discoverable.

#### Evolution

Founded from the control file; established as baseline in 2.4.0 per the control plane history.

### revision-accepted - 2026-08-06T21:08:00Z

```json
{
  "event_id": "adre_8396955a0aa57e737b22",
  "founding_source": ".memory-seed/index.md#L143",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
