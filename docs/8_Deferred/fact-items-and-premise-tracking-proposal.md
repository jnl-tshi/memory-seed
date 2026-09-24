---
title: "Fact items and decision premise tracking"
date: "2026-09-24"
status: deferred
priority: P2
deferred_reason: "A new Fact record kind and a decision-to-fact `rests_on` field would change the hosted record model, which capture-first P0 keeps to Decision and Documentation."
revisit_when: "The P0.4 thin slice works, the P1.5 tournament has measured record-kind and premise-extraction tasks, and curated volume shows decisions going stale because their premises changed."
source: "docs/4_Reference/atomic-facts-and-decisions-report.md (2026-09-24)"
next_action: "Deferred until the P0.4 loop and P1.5 tournament evidence exist; see revisit_when."
---

# Proposal: Fact Items and Decision Premise Tracking

## Current disposition

**DEFERRED — post-pilot candidate.** The
[atomic facts and decisions report](../4_Reference/atomic-facts-and-decisions-report.md) proposes items that
are either DECISION or FACT. The cheap parts of that report are carried into existing tranches (see below).
The schema-changing core is parked here:

- a non-authoritative **FACT** record kind (`observation`, `measurement`, `constraint`, `assumption`,
  `definition`). Each fact has a `volatility` value and is replaced via `replaces`, never edited;
- a **`rests_on`** field recording which facts a decision depends on. It is a field, not a new
  relationship kind, following the precedent of the ADR ledger's `supporting_decisions`;
- **premise-change flags**: when a fact is replaced, the decisions and ADR heads resting on it show
  `premise_changed` as advisory metadata. They are never demoted or rewritten automatically;
- retrieval of fact hits rolled up to the decisions they support, plus claim-only embedding text.

These affect the hosted SQL record model (P0.3/P0.4 entities) and the local Markdown substrate (the fact
ref grammar and item sidecars). So they need their own design discovery once the evidence gates in
`revisit_when` are met.

## Already carried into active tranches

| Report element | Tranche |
|---|---|
| Agreement span plus user/agent attribution kept in synthetic golden sessions | P0.2 design discovery |
| Decision atomicity (one issue, one chosen option, one scope; agreement test) and 40–120 character verbatim grounding quotes as curator acceptance rules; record kinds unchanged | P0.4 design discovery |
| Record-kind (fact / decision / documentation / none), decision-split and premise-extraction tasks; `supports` treated as the `rests_on` field, not a new relationship kind | P1.5 tournament design discovery |
| Claim-only embedding and fact rollup evaluation | P1.8 retrieval parity, or the local semantic-compression benchmark |

## Open questions to settle at revisit

The report's open questions 1–5 and 7–9 remain open. Question 6 (the curator's input boundary) is answered
for hosted by the bounded evidence window in the
[hosted programme](../2_Todo/hosted-memory-mvp-programme.md#curator-pipeline).
