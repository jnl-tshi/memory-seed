---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_proposal_completion_moves_lane
title: A proposal moves lane when its acceptance criteria are met, and stays there
topics:
  - docs-lifecycle
  - proposal-lifecycle
  - decision-harvest
created_at: 2026-08-08T03:10:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# A proposal moves lane when its acceptance criteria are met, and stays there

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

A proposal moves to the completed lane when its acceptance criteria are fully met, and stays there as a historical record even when a newer active proposal cites it. A source report moves once its actionable recommendations have been split into their own plans.

### Why

Separating unresolved from active from finished keeps the roadmap trustworthy - a reader can tell an open question from shipped work without reading either. Leaving a completed document in place because something still references it is what turns historical research into apparent current planning.

### How it evolved

2026-07-02 separated completed from active work; 2026-07-04 formalised the lifecycle as a seeded skill with a coverage matrix; 2026-07-05 moved the logic-capture source report across once all six of its recommendations had shipped.

### Constitution

- `constitution:v1#folder-lifecycle` (governing)
- `constitution:v1#explainability` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:10:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#folder-lifecycle",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#explainability",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_9m2jk06hgx7ctrm1:d3",
  "event_id": "adre_2ff464dea6d60c6029b3",
  "source": "derived",
  "supporting_decisions": [
    "mse_bqc8am1yq8sv5s92:d1",
    "mse_r1ey59bbv1jsseth:d1"
  ],
  "update_entry_id": "mse_9m2jk06hgx7ctrm1"
}
```

#### Decision

A proposal moves to the completed lane when its acceptance criteria are fully met, and stays there as a historical record even when a newer active proposal cites it. A source report moves once its actionable recommendations have been split into their own plans.

#### Why

Separating unresolved from active from finished keeps the roadmap trustworthy - a reader can tell an open question from shipped work without reading either. Leaving a completed document in place because something still references it is what turns historical research into apparent current planning.

#### Evolution

2026-07-02 separated completed from active work; 2026-07-04 formalised the lifecycle as a seeded skill with a coverage matrix; 2026-07-05 moved the logic-capture source report across once all six of its recommendations had shipped.
