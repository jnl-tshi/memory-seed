---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_session_decision_authority
title: Session-decision authority and ADR-curated synopsis
topics:
  - schema
created_at: 2026-08-03T15:40:05Z
user_initials: JNL
agent_type: codex
source: write-time
---

# Session-decision authority and ADR-curated synopsis

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_17d0qqh34a07qp5b:d1`

### Decision

Keep session decisions authoritative evidence while living ADRs curate concise concern-specific authority and evolution.

### Reason

One detailed source remains fetchable and immutable while several architectural concerns can review and summarize the same decision without duplicating evidence authority.

### Impact

Converges the original partitioned-authority proposal and decision-envelope lens into an explicit living ADR authority boundary.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-03T15:40:05Z

```json
{
  "decision_ref": "mse_ddeat5w29spep3qw:d1",
  "event_id": "adre_88006aeb38c99ec38f71",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_z7rfq8x5qjfbyzdc:d1",
      "relation_assertion": "link:mse_ddeat5w29spep3qw:d1:evolves:mse_z7rfq8x5qjfbyzdc:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_kbc2mq9972ppy1vw"
}
```

#### Decision

Keep session decisions as detailed evidence authority while ADRs curate concern membership, synopsis, and governing head.

#### Reason

The split gives humans a concise current view without duplicating or rewriting the authoritative decision record.

#### Impact

Refines the original consolidation proposal into an explicit authority boundary for living ADRs.

### revision-accepted - 2026-08-03T15:40:06Z

```json
{
  "decision_ref": "mse_ddeat5w29spep3qw:d1",
  "event_id": "adre_d86ace1dda72ef5be009",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_kbc2mq9972ppy1vw"
}
```

#### Decision

Accept mse_ddeat5w29spep3qw:d1.

#### Reason

Accepted as the authority-partition head before converging evolution.

#### Impact

mse_ddeat5w29spep3qw:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-03T15:41:00

```json
{
  "decision_ref": "mse_17d0qqh34a07qp5b:d1",
  "event_id": "adre_d855aee5c266c1133ef6",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_ddeat5w29spep3qw:d1",
      "relation_assertion": "link:mse_17d0qqh34a07qp5b:d1:evolves:mse_ddeat5w29spep3qw:d1"
    },
    {
      "decision": "mse_z7rfq8x5qjfbyzdc:d1",
      "relation_assertion": "link:mse_17d0qqh34a07qp5b:d1:evolves:mse_z7rfq8x5qjfbyzdc:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_17d0qqh34a07qp5b"
}
```

#### Decision

Keep session decisions authoritative evidence while living ADRs curate concise concern-specific authority and evolution.

#### Reason

One detailed source remains fetchable and immutable while several architectural concerns can review and summarize the same decision without duplicating evidence authority.

#### Impact

Converges the original partitioned-authority proposal and decision-envelope lens into an explicit living ADR authority boundary.

### revision-accepted - 2026-08-03T15:41:12Z

```json
{
  "decision_ref": "mse_17d0qqh34a07qp5b:d1",
  "event_id": "adre_1f5318fb869eff6f106e",
  "expected_authoritative_decision": "mse_ddeat5w29spep3qw:d1",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_17d0qqh34a07qp5b"
}
```

#### Decision

Accept mse_17d0qqh34a07qp5b:d1.

#### Reason

Accepted as the intended converged authority boundary.

#### Impact

mse_17d0qqh34a07qp5b:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.

### reviewed-no-change - 2026-08-10T13:00:00

```json
{
  "decision_ref": "mse_axkrkd339br970kw:d2",
  "event_id": "adre_2d9a35247b08eb9beb22",
  "impact_provenance": "preserved",
  "matched_decisions": [
    "mse_17d0qqh34a07qp5b:d1"
  ],
  "source": "write-time",
  "update_entry_id": "mse_axkrkd339br970kw"
}
```

#### Decision

Retain mse_axkrkd339br970kw:d2 as the governing decision.

#### Reason

CLI parity and the standalone recorder preserve the existing split: session entries remain detailed evidence authority while ADRs curate concern-specific heads and synopsis.

#### Impact

The review retained the governing decision; the original impact was not otherwise recorded.
