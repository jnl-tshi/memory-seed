---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_session_layout
title: Month-grouped session layout; per-user gated on 2+ participants
topics:
  - session-logging
  - multi-user-sessions
created_at: 2026-08-06T17:03:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Month-grouped session layout; per-user gated on 2+ participants

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Session document discovery uses iter_session_documents() to read legacy flat session files (sessions/YYYY-MM-DD.md), new month-grouped flat files (sessions/YYYY-MM/YYYY-MM-DD.md), and new month-grouped per-user files (sessions/YYYY-MM/YYYY-MM-DD/<user>.md). Per-user layout activates only when 2+ participants are registered.

### Why

Month grouping organizes session history by calendar period for better discoverability; per-user gating prevents fragmentation for single-user projects while supporting team workflows when participants are declared.

### How it evolved

Founded from the control file; no session lineage attached yet.

### Constitution

- `constitution:v1#markdown-authority` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:03:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "event_id": "adre_63603613f787b33f8fbf",
  "founding_quote": "Session document discovery: package readers use `iter_session_documents()` in `core.py` to read legacy flat session files (`sessions/YYYY-MM-DD.md`), legacy per-day/per-user files (`sessions/YYYY-MM-DD/<user>.md`), new month-grouped flat files (`sessions/YYYY-MM/YYYY-MM-DD.md`), and new month-grouped per-user files (`sessions/YYYY-MM/YYYY-MM-DD/<user>.md`).",
  "founding_source": ".memory-seed/index.md#L147",
  "source": "derived",
  "supporting_decisions": [
    "mse_ed8zaf52k3eyaxqv:d1"
  ]
}
```

#### Decision

Session document discovery uses iter_session_documents() to read legacy flat session files (sessions/YYYY-MM-DD.md), new month-grouped flat files (sessions/YYYY-MM/YYYY-MM-DD.md), and new month-grouped per-user files (sessions/YYYY-MM/YYYY-MM-DD/<user>.md). Per-user layout activates only when 2+ participants are registered.

#### Why

Month grouping organizes session history by calendar period for better discoverability; per-user gating prevents fragmentation for single-user projects while supporting team workflows when participants are declared.

#### Evolution

Founded from the control file; no session lineage attached yet.
