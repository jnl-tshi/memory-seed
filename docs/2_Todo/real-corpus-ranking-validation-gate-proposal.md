---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - retrieval
  - graph
  - testing
---

# Real-corpus A/B as a required gate before any default ranking flip

Status: **PROMOTED to `2_Todo`** 2026-07-14 (active — approved by JNL). Filed 2026-07-13.
Priority: P2 — hardens the ranking change-discipline; small tooling + a contract amendment.
Next action: build `memory-seed ranking-ab` and amend the graph-edge-contract "Expose before you rank"
rule to require a real-corpus A/B before any default flip. **Sequence first** in the promoted
ranking/graph-quality track — it is the gate the successor-surfacing replacement boost waits on.
Source: This session — the advisor caught that fixtures alone hadn't proven the flip.

## Problem — "fixtures on a branch" is necessary but not sufficient

The graph-edge contract's standing rule is **"Expose before you rank … default `memory_search` ranking
stays stable until a signal proves useful against fixtures on a branch"**
(`graph-edge-contract.md`, "Standing rules"). This session showed the gap in that bar: the
supersession-damping fixtures were green, yet an independent review caught that the **strict** criterion
("the live replacement out-ranks the decision it retires") was only verified on **one** of two real
supersession lineages. What actually justified the flip was a hand-rolled **real-corpus A/B** (flag
on/off over this repo's live memory, comparing full-corpus ranks of each retired entry vs its
replacement). Two problems:

1. That real-corpus step is **not required** by the rule — the next person flipping a ranking default
   could stop at green fixtures, exactly the trap the advisor caught here.
2. It was a **throwaway script**, not reusable tooling — every future flip re-invents it.

Constructed fixtures prove the *mechanism* fires; only the real corpus proves it *helps live queries
without regressing ordinary ones*.

## Current behavior (grounded)

- `graph-edge-contract.md` "Expose before you rank" gates a default flip on *fixtures on a branch*. The
  supersession graduation note I added this session mentions "fixtures **and** a real-corpus check" —
  but only as a **description of what happened**, not a codified requirement, and there is no tool.
- `freshness-aware-memory-ranking-proposal.md` records the A/B narrative; nothing reusable remains.

## Proposal

1. **Amend the rule.** Update "Expose before you rank" so a ranking signal may flip **default-on** only
   after *(a)* fixtures on a branch **and** *(b)* a real-corpus A/B that shows the intended improvement
   on real lineages **and** no regression on queries lacking the signal. Fixtures prove the mechanism;
   the corpus proves the benefit.
2. **Ship the tool.** `memory-seed ranking-ab --signal <name> [--query <q> ...]` runs the on/off
   comparison over the live corpus and prints, per affected entry, its rank with the signal off vs on
   (full-corpus positions, not just the default window — the #10-outside-top-8 case this session showed
   why full-k matters), plus a "queries with no affected hit are byte-identical" check. One command
   instead of a throwaway script.
3. **Library harness (optional).** Factor the A/B comparison so branch fixtures can call it directly,
   keeping fixture and real-corpus checks structurally identical.

## Non-goals

- Not a replacement for fixtures — both are required.
- No runtime gate; this is a branch/dev-time discipline (like the existing contract rule).
- Not tied to supersession — applies to any future default ranking signal.

## Acceptance criteria

- `ranking-ab --signal supersession_damping` reproduces this session's finding (live replacement
  out-ranks every retired predecessor at full k; no-hit queries byte-identical) as a repeatable command.
- The contract's "Expose before you rank" rule names the real-corpus A/B as a required pre-flip step.

## Relationship to existing coverage (checked — partial, this completes it)

- `docs/3_Spec/graph-edge-contract.md` — "Expose before you rank" (the rule this amends) and the
  supersession graduation note (which *describes* a real-corpus check but doesn't *require* one).
- `docs/5_Completed/freshness-aware-memory-ranking-proposal.md` — the ad-hoc A/B this turns into tooling.
- Distinct from `docs/2_Todo/completed/*` Trail golden-fixture work (that pins UI output, not ranking
  behavior).
