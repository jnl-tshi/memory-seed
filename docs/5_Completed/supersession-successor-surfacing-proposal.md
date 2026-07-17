---
memory-system-version: 2.18
implemented_by: 82fb7cc, 69a190e, cfaf4ba, 6265e04
shipped: 2026-07-15
tags:
  - memory-seed
  - proposal
  - retrieval
  - graph
---

# Supersession successor-surfacing (make the live replacement reachable, not just the retired one damped)

Status: **SHIPPED 2026-07-15.** `superseding_head` and the default-on, lineage-bounded successor boost
both shipped after fixtures and the real-corpus `ranking-ab` gate passed.
Disposition: Completed and moved from `docs/2_Todo/` to `docs/5_Completed/` on 2026-07-15.
Priority: Completed P2 — retrieval quality; closes the asymmetry the default-on dampener exposed.
Next action: None for this proposal; use the same expose-then-gate discipline for future ranking signals.
Source: This session's freshness-ranking validation.

## Problem — supersession ranking is asymmetric

`evolves` and `supersedes` are handled asymmetrically in the default ranking, and the gap only shows
under real queries:

- **`evolves`** *surfaces the successor*: every `memory_search` result carries `evolved_head` (the
  terminal head of the evolves lineage), so the current, fuller form is **reachable** even when the
  base entry is the hit.
- **`supersedes`** only *damps the predecessor*: a retired entry with a non-empty `superseded_by` is
  down-ranked, but nothing surfaces or lifts its replacement. The replacement id sits in the retired
  entry's `superseded_by` field — which rides on the very result that just got demoted out of the
  window.

The consequence, observed directly in the real-corpus A/B: on the "Retirement record" lineage the live
replacement (`mse_mkxdvaxvw99dz4s0`) out-ranked its retired predecessors but landed at **#10** — outside
the default `top_k=8` window. Damping the old entry doesn't *lift* the new one; it just lets the
next-best matches fill in. So a query about a superseded topic can leave the agent seeing neither the
(damped) retired decision **nor** its replacement in the default window. Now that damping is on by
default, that's the common case, not an edge case.

## Previous behavior (grounded)

- `evolves`: `search_memory` computes `evolved_head` via `evolves_lineage_heads` and attaches it to each
  result (additive, read-only) — see `graph-edge-contract.md` "Supersession rank-dampener" bullet and
  `freshness-aware-memory-ranking-proposal.md` item 2.
- `supersedes`: `superseded_by` was exposed on results and drove the dampener (`freshness-...` item 1),
  but there was no successor pointer or replacement boost. This proposal supplied both missing halves.

## Proposal — give supersedes the successor half evolves already has

1. **SHIPPED — `superseding_head` (surface, additive first).** Symmetric with `evolved_head`: follow the
   `superseded_by` chain forward to the terminal live replacement (reuse the `evolves_lineage_heads`
   pattern — the palette lineage `mse_903ba3 → mse_jt2rs0 → mse_6dzkmp` is exactly such a chain) and
   attach it to a retired entry's result. Read-only, changes no ordering — the "expose before you rank"
   first step.
2. **SHIPPED — replacement boost (ranking, behind the shipped gate).** When a retired entry that matches a query is
   damped, apply a small *boost* to its terminal replacement so the **current** decision enters the
   window — the mirror of the dampener. Bounded so it never fabricates relevance (only lifts an entry
   that already matches the query at all); off until fixtures **and** a real-corpus A/B prove it (per
   the completed ranking-validation-gate proposal).
3. **SHIPPED — composition preserved.** Recency and the dampener are unchanged.

## Non-goals

- Do **not** un-damp the retired entry — the dampener stays; this adds a successor pointer/boost.
- Do **not** hard-inject the replacement into results — surface it (step 1) and, at most, boost it into
  the window (step 2); never force it above better matches.
- Respect `exclude_superseded` (membership) and the down-rank-only / never-hide constraint.

## Acceptance criteria

All criteria passed on 2026-07-15, including chain fixtures, no-hit controls, lineage-bounded boost
regressions, and the full-corpus `superseding_successor_boost` A/B gate.

- A query matching a retired entry carries `superseding_head` = its terminal live replacement.
- With the boost on, the live replacement enters the default window on both real lineages (palette;
  Explorer/Lense "Retirement record") without displacing better non-lineage matches.
- Fixtures cover a supersedes chain (surface + boost) and confirm evolves behavior is untouched;
  default-window queries with no superseded hit stay byte-identical.

## Relationship to existing coverage (checked — not a duplicate)

- `docs/5_Completed/freshness-aware-memory-ranking-proposal.md` — item 1 (dampener) + item 2 (evolves
  `evolved_head`). This is the **missing symmetric item 3** (supersedes successor), not a re-proposal.
- `docs/3_Spec/graph-edge-contract.md` — "Supersession rank-dampener" section documents damp-only for
  supersedes and `evolved_head` for evolves; this closes that asymmetry.
- `docs/5_Completed/evolution-edges-plan.md` / `docs/5_Completed/supersession-edges-plan.md` — the
  `evolved_head` precedent and the harmony constant this mirrors.
