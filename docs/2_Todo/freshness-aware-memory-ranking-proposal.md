---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - retrieval
  - graph
---

# Freshness-aware memory ranking (supersession-dampen + evolves-successor-surface)

Status: **LANDED - on by default** (2026-07-13, user-requested). Shipped default-off on
`feature-freshness-ranking`, then turned on by default on `feature-freshness-default-on` after a
real-corpus A/B on both live supersession lineages (the Trail palette chain and the Explorer/Lense-era
"Retirement record" that superseded two 3.0-plan decisions).
Priority: P2 — retrieval quality; touches the ranking contract, so it carries that contract's
change-discipline (fixtures-on-a-branch before default-on).
Source: User 2026-07-13 — "recency of the data must be an important signal, especially if it has an
evolves or replaces signal … the links are also living in the sidecar so take that into account."
Companion to `proactive-history-retrieval-discipline-proposal.md`: making agents "retrieve the why"
is only safe if retrieval surfaces the **current** why, not a retired decision ranked high.
Scope: Take supersession/evolution from *exposed signals* to *ranking signals* in default
`memory_search`, drawing them from the sidecar-augmented effective edge set.
Non-goals: No change to recency (already ranked). No change to the deliberate evolves≠supersedes
semantics. No hard exclusion by default (`exclude_superseded` stays the opt-in filter). No ranking
flip until fixtures prove it.

## Guiding constraint (must hold — user, 2026-07-13)
**Memory ranking adds freshness *context*; it must never stop the agent from finding the actual live
condition of the repository, and it must never hide information — it only adds context to the
situation.**

- The repository's live condition (what the code/files are **now**) is found by reading the **files**,
  the source of truth — never by `memory_search`. This proposal re-orders only the *reasoning/context*
  layer; it does not gate discovery of current state. (Keeps the `agent-rules.md` "History Retrieval"
  line intact: current files are authority, session history is evidence and reason.)
- A surfaced supersession is a **decision record to verify against the code**, not a claim the code
  already changed. Implementation can lag the decision, so a "superseded" entry is context that says
  *"this was decided to be replaced"* — the agent still reads the file to see whether it actually was.
- **Down-rank only, never a default hard-exclude.** A superseded/older entry stays fully retrievable
  (just lower); no reasoning the agent might need is removed from view. `exclude_superseded` remains an
  explicit, caller-chosen filter.

Any implementation that would suppress, hide, or substitute-for the live file/code state - rather than
merely add the freshness dimension to context - is out of scope and violates this constraint.

## Current behavior (grounded)
- **Recency is already a default ranking factor:** `final_score = match_score * recency_multiplier`
  ([`semantic_cache.py:585`](../../memory_seed/semantic_cache.py), exponential decay by entry age). So
  "recency matters" is already true.
- **The lifecycle signal is already sidecar-aware:** `search_memory` calls
  `augment_chunks_with_link_sidecars(...)` **before** building the graph
  ([`retrieval.py:89`](../../memory_seed/retrieval.py)) and computes `superseded_by` from that
  augmented graph ([`retrieval.py:127`](../../memory_seed/retrieval.py)). A supersession authored
  *later in a link sidecar* already counts (MCP sidecar-parity closed the last gap).
- **But supersession does not shape the default *order*:** `superseded_by` is (a) exposed on results,
  (b) an opt-in `exclude_superseded` hard filter, and (c) a ×0.25 damper on the graph's
  `importance_score` - and `importance_score` is **not** a term in `final_score`. So a **replaced**
  decision can out-rank its replacement in the default order.
- **Evolves is deliberately never damped** (`SUPERSEDED_IMPORTANCE_DAMPING` applies only to
  `superseded_by`; `evolution-edges-plan.md` keeps evolves "valid but incomplete"), so an evolved
  entry must **not** be down-ranked.

## Why it's this way (not an oversight)
The graph-edge contract's standing rule: **"Expose before you rank. New derived signals are surfaced
read-only first; default `memory_search` ranking stays stable until a signal proves useful against
fixtures on a branch."** ([`graph-edge-contract.md:176`](../3_Spec/graph-edge-contract.md)).
Supersession was exposed first, on purpose. This proposal is the next stage of that same plan.

## Proposal
1. **Supersession rank-dampener (replaces).** Fold a multiplicative damper into `final_score` when an
   entry has a non-empty `superseded_by`: `final_score *= SUPERSEDED_RANK_DAMPING` (reuse or mirror the
   0.25 harmony constant). A replaced decision then sinks beneath its live replacement unless nothing
   fresher matches at all - so it stays retrievable (never a hard drop; that remains
   `exclude_superseded`). Draw `superseded_by` from the already-sidecar-augmented graph, so
   sidecar-authored supersessions dampen too.
2. **Evolves successor-surfacing (extends).** Do **not** dampen an evolved entry. Instead, when a hit
   has `evolved_by`, surface/point to the successor (e.g. a small boost to the head-of-lineage entry,
   or a result annotation "extended by <id>") so the retriever reads the *current, fuller* form
   without burying the still-valid original. Follow the chain to the head where cheap.
3. **Recency stays as-is** - already the dominant freshness term; the lifecycle dampers compose with
   it multiplicatively (a fresh replacement beats an old superseded original on both axes).

## Rollout / guardrail (respect the contract)
- Implement behind the existing behavior first: keep the dampener **off by default**, add fixtures on
  a branch - a superseded decision + its replacement (both YAML and *sidecar*-authored supersession),
  and an evolves chain - asserting the live/current entry ranks above the retired one and that an
  evolved-but-valid entry is not buried. Flip default-on only once the fixtures prove it doesn't harm
  ordinary topical search. **Done (2026-07-13):** fixtures landed default-off, then a real-corpus A/B
  cleared the bar - on both live supersession lineages the replacement out-ranked every retired
  predecessor at full k, the retired entries stayed retrievable (down-rank only, e.g. #1 -> #45), and
  queries with no superseded hit in-window were byte-identical - so `supersession_damping` is now on by
  default in `search_memory` + the MCP `memory_search` tool, with `supersession_damping=False` the
  opt-out.
- `exclude_superseded` remains the caller's hard-filter escape hatch; this changes *order*, not
  *membership*.
- Update `graph-edge-contract.md`'s ranking section + `docs/2_Todo/completed/supersession-edges-plan.md`
  provenance when it lands (the "expose before you rank" line graduates for supersession).

## Acceptance criteria
- Default `memory_search` ranks a live replacement above the decision it supersedes, including when the
  supersedes edge lives only in a link sidecar.
- An evolved-but-valid entry is not down-ranked; its successor is surfaced so the head of the lineage
  is reachable.
- Recency behavior is unchanged; `exclude_superseded` still hard-filters.
- Fixtures cover YAML-authored and sidecar-authored supersession and an evolves chain; ordinary search
  ordering is not regressed.

## Dependencies / relationship
- `proactive-history-retrieval-discipline-proposal.md` (the behavior half - retrieve the why; this is
  the ranking half - make the *current* why surface).
- `docs/2_Todo/completed/supersession-edges-plan.md` (the ×0.25 harmony constant + exposure staging).
- `docs/2_Todo/evolution-edges-plan.md` (evolves-stays-valid semantics this must preserve).
- `docs/3_Spec/graph-edge-contract.md` (the ranking-change discipline and the edge definitions).
