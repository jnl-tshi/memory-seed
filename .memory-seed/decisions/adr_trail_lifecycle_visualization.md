---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_trail_lifecycle_visualization
title: "Trail: lifecycle visualization and decision-level row rendering"
topics:
  - memory-trace
  - ui-design
  - lifecycle-edges
created_at: 2026-08-08T03:04:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Trail: lifecycle visualization and decision-level row rendering

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

The Trail displays lifecycle edges (supersedes/evolves/related) between entries and decisions by default, ranked by precision into three classes: decision-to-decision and entry-to-decision edges drawn solid and bold, entry-to-entry edges drawn dashed and light. Multi-decision entries render one Trail row per decision, grouped under an anchor row, with edge selection scoped by entry so clicking any row in a group lights the entire entry's lineage.

### Why

The decision-level edges were recorded but invisible - every decision-level edge drew only on select, so the finest lineage links in the corpus were dark until clicked, and 189 entry-level evolves were equally hidden. Draw all three classes and let weight and opacity carry hierarchy, so history links read as quiet background rather than a wall. Decision rows must compute visibility and grouping by entry identity because selection state is entry-scoped, which is what stops a group from splitting.

### How it evolved

2026-07-18 shipped the vanilla Trail as a B0b presentation mode; 2026-07-19 stabilised scroll and opened a new corpus at the top; 2026-07-21 surfaced decisions as Trail rows via section chunks, then made D1 a heading with D2..DN as subheadings; 2026-07-24 drew all lifecycle edges by default with three-class weighting.

### Constitution

- `constitution:v1#explainability` (governing)
- `constitution:v1#evidence-first` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:04:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#explainability",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#evidence-first",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_zm2h343r4shfre3j:d2",
  "event_id": "adre_f8500f2c02f28bf9e6e2",
  "source": "derived",
  "supporting_decisions": [
    "mse_74fb71s2cdrwqrqp:d1",
    "mse_dgc0zvchsqpvjpe7:d1",
    "mse_dgc0zvchsqpvjpe7:d2",
    "mse_9wsn23n3k8txnm2m:d1",
    "mse_t5bbdstgmqzagn2y:d1"
  ],
  "update_entry_id": "mse_zm2h343r4shfre3j"
}
```

#### Decision

The Trail displays lifecycle edges (supersedes/evolves/related) between entries and decisions by default, ranked by precision into three classes: decision-to-decision and entry-to-decision edges drawn solid and bold, entry-to-entry edges drawn dashed and light. Multi-decision entries render one Trail row per decision, grouped under an anchor row, with edge selection scoped by entry so clicking any row in a group lights the entire entry's lineage.

#### Why

The decision-level edges were recorded but invisible - every decision-level edge drew only on select, so the finest lineage links in the corpus were dark until clicked, and 189 entry-level evolves were equally hidden. Draw all three classes and let weight and opacity carry hierarchy, so history links read as quiet background rather than a wall. Decision rows must compute visibility and grouping by entry identity because selection state is entry-scoped, which is what stops a group from splitting.

#### Evolution

2026-07-18 shipped the vanilla Trail as a B0b presentation mode; 2026-07-19 stabilised scroll and opened a new corpus at the top; 2026-07-21 surfaced decisions as Trail rows via section chunks, then made D1 a heading with D2..DN as subheadings; 2026-07-24 drew all lifecycle edges by default with three-class weighting.
