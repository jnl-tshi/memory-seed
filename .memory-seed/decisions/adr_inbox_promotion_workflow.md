---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_inbox_promotion_workflow
title: "Inbox promotion: conservative triage, one owner per workstream"
topics:
  - proposal-lifecycle
  - documentation
  - decision-harvest
created_at: 2026-08-08T03:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Inbox promotion: conservative triage, one owner per workstream

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Inbox items are promoted to the active roadmap only when evidence supports actionability. Where many proposals overlap, a distilled crosswalk becomes the surviving record and the individual sources are retired once their deltas are confirmed or merged into an active owner. Every workstream has exactly one owner.

### Reason

The inbox accumulated overlapping proposals drafted against stale assumptions, several of which read as missing capability only because they predated the code that shipped them. One distilled crosswalk plus deliberate ownership prevents competing contracts and duplicated lifecycle tracking, and keeps the roadmap something a reader can trust.

### Impact

2026-07-08 promoted actionable graph and topic ideas into the roadmap; 2026-07-16 rebaselined the platform review against shipped state and folded 14 inbox documents into owned roadmap items; 2026-07-20 retired both proposal sets, leaving the crosswalk as the surviving record.

### Constitution

- `constitution:v1#markdown-authority` (governing)
- `constitution:v1#single-source` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#single-source",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_2geqfa8tg182a77p:d1",
  "event_id": "adre_e98a9fbcea1537edcac3",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_d2daxtnv8eqx4vqr:d1",
    "mse_mazbt6cek8m8a6st:d1",
    "mse_ddba1ztxqhasfbwf:d2",
    "mse_wjntbg88n3m0qjss:d1",
    "mse_y9q4bnv2yckk6w74:d1",
    "mse_tx1c338ca1ybr666:d1"
  ],
  "update_entry_id": "mse_2geqfa8tg182a77p"
}
```

#### Decision

Inbox items are promoted to the active roadmap only when evidence supports actionability. Where many proposals overlap, a distilled crosswalk becomes the surviving record and the individual sources are retired once their deltas are confirmed or merged into an active owner. Every workstream has exactly one owner.

#### Reason

The inbox accumulated overlapping proposals drafted against stale assumptions, several of which read as missing capability only because they predated the code that shipped them. One distilled crosswalk plus deliberate ownership prevents competing contracts and duplicated lifecycle tracking, and keeps the roadmap something a reader can trust.

#### Impact

2026-07-08 promoted actionable graph and topic ideas into the roadmap; 2026-07-16 rebaselined the platform review against shipped state and folded 14 inbox documents into owned roadmap items; 2026-07-20 retired both proposal sets, leaving the crosswalk as the surviving record.
