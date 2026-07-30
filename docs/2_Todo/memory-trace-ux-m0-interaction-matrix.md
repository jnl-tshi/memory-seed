---
title: "Memory Trace UX M0 interaction matrix"
status: active
priority: P1
next_action: "Implement M2 Trail history orientation and filtering against the named fixtures."
blocked_by: []
sources:
  - memory-trace-ux-reference-model-implementation-plan.md
  - ../3_Spec/memory-trace-trail-search-and-graph-ux.md
---

# Memory Trace UX M0 Interaction Matrix

Status: **M0 and M1 delivered 2026-07-30.** This is the single reconciliation point for the UX reference-model plan. It records implementation truth; it does not create a second semantic or data contract.

## Frozen terms and ownership

| Term | Meaning | Authoritative input | Boundary |
| --- | --- | --- | --- |
| Trail | Default chronological decision-history workspace. | `/api/v1/trail` and Git-derived provenance. | Does not rewrite Git or Markdown. |
| Graph | Bounded relationship exploration around selected canonical objects. | `/api/v1/graph`; typed edges and derived topology. | Never owns relationships or layout as memory. |
| Inspector | Persistent selection detail region. | Selected entry/decision identity plus chunk/source data. | Read-only projection. |
| Reader | Decision-first presentation inside Inspector. | Canonical entry body, sidecars, and evidence refs. | M1 delivered; it remains a read-only projection. |
| Quick Open | Direct jump to a known object. | Canonical object identity. | M4 proposed; not free-text ranking. |
| Structured search | Transparent historical query with visible criteria. | `/api/v1/search` and explicit filters. | M4 proposed; no hidden AI translation. |
| Recorded | First-hand value stored in canonical Markdown at write time. | Entry or sidecar field with `source: write-time`. | Must link to its source. |
| Derived | Deterministic projection from canonical data or Git. | Versioned API/projection computation. | Must name calculation/revision. |
| Suggested | Reconstructed candidate not yet accepted into canonical memory. | Advisory evidence/confidence only. | Never styled or treated as authoritative. |

## Behaviour and fixture matrix

| Behaviour | Status | Input / projection | UI surface | Keyboard / a11y expectation | Fixture / acceptance test |
| --- | --- | --- | --- | --- | --- |
| Chronological Trail with decision rows | Delivered | `TrailEvent`, `(entry_id, dN)` | Trail | Rows are buttons; selected row stays identifiable. | `memory-trace/client/src/trailModel.test.ts` |
| Direct main spine across integration | Delivered | Trail provenance and merge range | Trail lanes | Legend and row labels do not rely on colour alone. | `trailModel.test.ts` main-trunk regression |
| Shared selection leaves graph layout stable | Delivered | selected entry/decision identity | Trail, Graph, Inspector | Focus/selection remains inspectable. | Graph debug parity surface |
| Area/Activity ontology navigation | Delivered | declared decision topic sidecars and `ontology` facet | Navigation tree | Hierarchy is keyboard-operable; selection expands ancestors. | `TreeView.tsx` topic fixtures |
| Semantic lineage distinct from provenance lanes | Delivered | typed lifecycle edges | Trail and Graph | Edge type remains named, not colour-only. | Trail edge-rendering tests |
| Decision reader and exact evidence return | Delivered (M1) | entry body, typed Trail sidecar projection, evidence anchor | Inspector / Reader | Keyboard action opens exact Markdown and returns to the unchanged decision/Trail context. | `decisionReaderModel.test.ts`: multi-decision, missing-source, superseded fixture; build/typecheck |
| Recorded / derived / suggested grammar | Delivered in Reader (M1) | provenance class and source anchor | Inspector / Reader | Text badge accompanies the state; missing evidence is explicit. | `decisionReaderModel.test.ts` provenance-state fixture |
| Quick Open, structured search, commands | Proposed (M4) | object IDs and explicit criteria | navigation | Every action is keyboard-operable; criteria visible. | Query-mode fixture |
| Highlight-first filtering | Proposed (M2) | canonical Trail window and query | Trail | Selection persists and changes announce. | Filtered-selection fixture |
| One-hop graph expansion with list equivalent | Proposed (M3) | graph node/edge fields | Graph | Expand/inspect has non-canvas route. | Bounded-neighbourhood fixture |
| Resume / deterministic attention | Deferred (M5) | local state plus integrity rules | optional home | Rule and remediation always named. | Attention-rule fixture |

## M0 exit decision

- Every M1–M5 behaviour now names its data owner; none creates a renderer-owned semantic field or canonical write path.
- M1 is complete: its reader/evidence-return fixture suite covers multi-decision, generated/source-control state, missing source, and a superseding decision edge.
- M2–M5 remain sequenced, not implied by current Trail or graph implementation.
