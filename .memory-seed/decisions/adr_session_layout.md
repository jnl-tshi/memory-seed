---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `mse_k2188xq5evwmdny9:d1`

### Decision

Session document discovery reads legacy flat session files at sessions/YYYY-MM-DD.md, new month-grouped flat files at sessions/YYYY-MM/YYYY-MM-DD.md, and new month-grouped per-user files at sessions/YYYY-MM/YYYY-MM-DD/<user>.md. Per-user file layout activates only when two or more participants are registered. The new month-grouped structure with optional per-user files is the canonical write target, while discovery still supports reading legacy flat files for backward compatibility.

### Reason

Month folders keep session discovery manageable as logs grow without breaking old projects or forcing automatic migrations. Per-user layout in multi-participant projects avoids conflicts and improves navigation. The migration path is explicit and auditable with backups preventing data loss. Removal of migrated flat sources prevents duplicate entry IDs when dual-read is in effect, while keeping the legacy discovery path open for historical repositories.

### Impact

The decision began with a conservative migration API that maps legacy flat-file sessions through the participants registry and writes to per-user files with backup and cleanup. It then established month-grouped structure as the canonical write target with per-user files gated on 2+ participants, while discovery patterns adapted to read from both legacy and new locations.

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
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_ed8zaf52k3eyaxqv:d1"
  ]
}
```

#### Decision

Session document discovery uses iter_session_documents() to read legacy flat session files (sessions/YYYY-MM-DD.md), new month-grouped flat files (sessions/YYYY-MM/YYYY-MM-DD.md), and new month-grouped per-user files (sessions/YYYY-MM/YYYY-MM-DD/<user>.md). Per-user layout activates only when 2+ participants are registered.

#### Reason

Month grouping organizes session history by calendar period for better discoverability; per-user gating prevents fragmentation for single-user projects while supporting team workflows when participants are declared.

#### Impact

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:24:00Z

```json
{
  "event_id": "adre_0be6119941ae1278e8d2",
  "founding_source": ".memory-seed/index.md#L147",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L147.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L147 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:11:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_k2188xq5evwmdny9:d1",
  "event_id": "adre_3bff0ec9c76629eb0412",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Session document discovery uses iter_session_documents() to read legacy flat session files (sessions/YYYY-MM-DD.md), new month-grouped flat files (sessions/YYYY-MM/YYYY-MM-DD.md), and new month-grouped per-user files (sessions/YYYY-MM/YYYY-MM-DD/<user>.md). Per-user layout activates only when 2+ participants are registered.

#### Reason

Rests on the session decision that instituted it: "Make `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md`, `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD/<user>.md`" (mse_k2188xq5evwmdny9:d1). This decision established the month-grouped session layout with per-user files as canonical write targets.

#### Impact

Founded from .memory-seed/index.md#L147; this revision moves the concern off that control-file line onto mse_k2188xq5evwmdny9:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:17:00Z

```json
{
  "decision_ref": "mse_k2188xq5evwmdny9:d1",
  "event_id": "adre_375b4c8e9f3843b9f563",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_k2188xq5evwmdny9:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_k2188xq5evwmdny9:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:17:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_k2188xq5evwmdny9:d1",
  "event_id": "adre_3de6a160d15f1d29a28d",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_ed8zaf52k3eyaxqv:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Session document discovery reads legacy flat session files at sessions/YYYY-MM-DD.md, new month-grouped flat files at sessions/YYYY-MM/YYYY-MM-DD.md, and new month-grouped per-user files at sessions/YYYY-MM/YYYY-MM-DD/<user>.md. Per-user file layout activates only when two or more participants are registered. The new month-grouped structure with optional per-user files is the canonical write target, while discovery still supports reading legacy flat files for backward compatibility.

#### Reason

Month folders keep session discovery manageable as logs grow without breaking old projects or forcing automatic migrations. Per-user layout in multi-participant projects avoids conflicts and improves navigation. The migration path is explicit and auditable with backups preventing data loss. Removal of migrated flat sources prevents duplicate entry IDs when dual-read is in effect, while keeping the legacy discovery path open for historical repositories.

#### Impact

The decision began with a conservative migration API that maps legacy flat-file sessions through the participants registry and writes to per-user files with backup and cleanup. It then established month-grouped structure as the canonical write target with per-user files gated on 2+ participants, while discovery patterns adapted to read from both legacy and new locations.

### revision-accepted - 2026-08-08T23:17:40Z

```json
{
  "decision_ref": "mse_k2188xq5evwmdny9:d1",
  "event_id": "adre_aa87d689dc4dfdffe1c5",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L147",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_k2188xq5evwmdny9:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_k2188xq5evwmdny9:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
