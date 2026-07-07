---
memory-system-version: 2.13
tags:
  - memory-seed
  - plan
  - ranking
  - graph
---

# Superseded-Entry Retrieval Filter - Scope

> **Status: IMPLEMENTED 2026-07-04 (unreleased).** The opt-in `exclude_superseded` parameter is on
> `memory_search` (default `false`); when set, entries with a non-empty `superseded_by` are dropped
> from that query's results only. Backend-only; no CLI/UI default. Source: surfaced during a
> 2026-07-03 cross-proposal synergy evaluation of `supersession-edges-plan.md` and
> `interaction-frequency-ranking-plan.md` against the current MCP filter surface - not the external
> `Memory-Seed Logic Capture Improvement.md` review the other five logic-capture plans derive from.
> Companion to [`supersession-edges-plan.md`](supersession-edges-plan.md) (defines
> `supersedes`/`superseded_by`) and
> [`interaction-frequency-ranking-plan.md`](interaction-frequency-ranking-plan.md) (defines the
> harmony-contract dampening this filter must not duplicate or contradict).

## Motivation

Since `supersession-edges-plan.md` shipped P1, every chunk exposes a computed `superseded_by`
inverse.
Today's `memory_search` metadata filters (`user`, `date_from`, `date_to`) have no way to narrow
results to only-current (non-superseded) entries. A caller who already understands supersession
semantics - a future Lense UI toggle, or an agent doing a "what's the current state" query - has no
way to ask for that directly; it would have to inspect `superseded_by` on every returned chunk itself.

## Constraint This Must Respect

`supersession-edges-plan.md` already makes an explicit, deliberate design decision this filter must
not contradict: **"Never hide, only deprioritize... A superseded entry stays fully retrievable"**
(restated for Option B as "never suppression"). The harmony-contract dampening in
`interaction-frequency-ranking-plan.md` already handles *default* retrieval behavior - a superseded
entry ranks lower but is never excluded from `memory_search`'s default results.

This plan is therefore **strictly opt-in narrowing, never a default filter and never a hard exclusion
unless explicitly requested** - the same opt-in shape as `date_from`/`date_to` (narrows an otherwise-
unfiltered result set only when the caller supplies it).

## What Exists Today

`superseded_by` now exists through `supersession-edges-plan.md` P1, so this proposal is unblocked.
The `user`/`date_from`/`date_to` filters are scalar frontmatter comparisons applied before ranking. A
superseded filter is qualitatively heavier: it needs the computed graph inverse (`superseded_by`,
built the same way `inbound` is in `build_related_entry_graph()`), not a flat frontmatter field -
plausibly why neither companion plan proposed it already, rather than an oversight.

## Design

- New optional `memory_search` parameter (name pending Open Decision 1 below), default `false` -
  preserves today's behavior exactly; superseded entries remain in results by default.
- When set: drop any chunk whose entry has a non-empty `superseded_by` from the result set for *this
  query only*. Implemented as a post-ranking filter, reusing `build_related_entry_graph()`'s computed
  inverse rather than re-deriving it.
- Never blended into default ranking math and never defaults to on - matches
  `interaction-frequency-ranking-plan.md`'s own "exposure before ranking changes" precedent: surface
  read-only / opt-in first, change default behavior only after real usage need is shown.

## Open Decisions

1. Parameter name: `exclude_superseded` vs. `current_only` vs. something else.
2. Whether `memory-seed link show` / other CLI surfaces also gain an equivalent flag, or this stays
   MCP-only until real usage shows the CLI needs it too.
3. Whether a future Lense UI toggle should default this on or off for its search view - a UI/UX
   decision, out of scope for this backend-only plan.

## Definition of Done (P1)

- `supersession-edges-plan.md` P1 has shipped, so the prerequisite `superseded_by` inverse exists.
- Filter parameter added to `memory_search`'s input schema, default `false`, documented as opt-in
  narrowing, not a default-behavior change.
- Fixture test proving: (a) default behavior is unchanged (superseded entries still returned when the
  flag is omitted or `false`), (b) a superseded entry is excluded only when the flag is `true`.
- Concise session log entry.

## Phasing

- **Startable now:** `supersession-edges-plan.md` P1 has shipped. Keep the increment backend-only and
  opt-in until real client usage shows a UI/CLI default is needed.
