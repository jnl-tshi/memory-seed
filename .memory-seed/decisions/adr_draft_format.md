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

Authoritative decision: `mse_mrrnd0wam54vjrpc:d1`

### Decision

DRAFTS is the current session decision-record mnemonic: D/R remain mandatory, A/F/T remain optional, and S is conditionally required when a repository artifact materially informed the decision.

### Reason

Direct source references preserve proposal-to-decision provenance without weakening append-only history or forcing invented sources for conversational decisions.

### Impact

New supplied S references are validated and retrievable as structured metadata; historical DRAFT records remain valid and unchanged.

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

### revision-proposed - 2026-09-14T02:45:00

```json
{
  "decision_ref": "mse_mrrnd0wam54vjrpc:d1",
  "event_id": "adre_61fa084d0bfa44c454a6",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "ms-db2d715c:d1",
      "relation_assertion": "link:mse_mrrnd0wam54vjrpc:d1:evolves:ms-db2d715c:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_mrrnd0wam54vjrpc"
}
```

#### Decision

DRAFTS is the current session decision-record mnemonic: D/R remain mandatory, A/F/T remain optional, and S is conditionally required when a repository artifact materially informed the decision.

#### Reason

Direct source references preserve proposal-to-decision provenance without weakening append-only history or forcing invented sources for conversational decisions.

#### Impact

New supplied S references are validated and retrievable as structured metadata; historical DRAFT records remain valid and unchanged.

### revision-accepted - 2026-09-14T02:46:00Z

```json
{
  "decision_ref": "mse_mrrnd0wam54vjrpc:d1",
  "event_id": "adre_2494ec18f16e95b48e80",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L143",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_mrrnd0wam54vjrpc"
}
```

#### Decision

Accept mse_mrrnd0wam54vjrpc:d1.

#### Reason

JNL approved the DRAFTS source-attribution plan and explicitly directed its implementation on 2026-09-14.

#### Impact

mse_mrrnd0wam54vjrpc:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
