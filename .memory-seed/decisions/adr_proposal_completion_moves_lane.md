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
Status: **Accepted**

Authoritative decision: `mse_9m2jk06hgx7ctrm1:d3`

### Decision

A proposal moves to the completed lane when its acceptance criteria are fully met, and stays there as a historical record. This applies to individual plan documents, collections of related documents, and source reports whose actionable recommendations have all been split into their own plans and completed. Completed documents remain in place even when newer active proposals cite them, maintaining clarity between shipped work and current planning.

### Why

Separating unresolved from active from finished keeps the roadmap trustworthy - a reader can distinguish an open question from shipped work without reading either. Leaving a completed document in place because something references it prevents historical research from being mistaken for current planning. The acceptance criteria recognize that a source report's completion depends on its recommendations being implemented as separate plans.

### How it evolved

The decision began with moving NEXT_STEPS.md to docs/todo/ and establishing the pattern of fixing references when documents relocate. It then evolved to moving completed individual plan documents into a docs/todo/completed/ subfolder with updated roadmap language. Finally it clarified the rule applies to source reports whose actionable recommendations have all been split into now-completed plans.

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

### revision-rejected - 2026-08-08T23:14:00Z

```json
{
  "decision_ref": "mse_9m2jk06hgx7ctrm1:d3",
  "event_id": "adre_64f9b10566b8c16a334c",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

### revision-proposed - 2026-08-08T23:14:20Z

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
  "event_id": "adre_c520d776badab4b48bde",
  "source": "derived",
  "supporting_decisions": [
    "mse_bqc8am1yq8sv5s92:d1",
    "mse_r1ey59bbv1jsseth:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

A proposal moves to the completed lane when its acceptance criteria are fully met, and stays there as a historical record. This applies to individual plan documents, collections of related documents, and source reports whose actionable recommendations have all been split into their own plans and completed. Completed documents remain in place even when newer active proposals cite them, maintaining clarity between shipped work and current planning.

#### Why

Separating unresolved from active from finished keeps the roadmap trustworthy - a reader can distinguish an open question from shipped work without reading either. Leaving a completed document in place because something references it prevents historical research from being mistaken for current planning. The acceptance criteria recognize that a source report's completion depends on its recommendations being implemented as separate plans.

#### Evolution

The decision began with moving NEXT_STEPS.md to docs/todo/ and establishing the pattern of fixing references when documents relocate. It then evolved to moving completed individual plan documents into a docs/todo/completed/ subfolder with updated roadmap language. Finally it clarified the rule applies to source reports whose actionable recommendations have all been split into now-completed plans.

### revision-accepted - 2026-08-08T23:14:40Z

```json
{
  "decision_ref": "mse_9m2jk06hgx7ctrm1:d3",
  "event_id": "adre_76b176261c67d57eba49",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```
