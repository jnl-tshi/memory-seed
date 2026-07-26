---
priority: P2
next_action: JNL to accept or reject. If accepted the order is - (1) `parent:` field + schema_version 2 + read-time ancestor derivation, (2) reclassify the aliases that are really children, (3) point community colour at the parent level and grouping at the child level, (4) only then any topic sweep. Blocks and supersedes the flat splits recommended in topic-vocabulary-concentration-review.md.
---

# Hierarchical topic vocabulary: parent subsystems, child subsystems

Status: **PROPOSAL — 2026-07-26.** Raised by JNL after the concentration review: *"reframe the
hierarchy in the topics so that it covers topics which subsystem parents and subsystems children, and
the same might be useful for activities"*, and then — the point that ties it to the graph — *"if the
definitions are framed in this way the communities should also be generated more easily at decision
level granularity."*

## The hierarchy already exists. It has been crushed into the alias field.

`aliases:` is documented as spelling variants — "prefer renaming via `aliases:` over deleting". In
practice it has been carrying two different relations at once:

| relation | example | correct home |
|---|---|---|
| **spelling variant** (same concept) | `memory-trace-ui` → `memory-trace`, `perf` → `performance` | alias |
| **narrower concept** (child) | `continuity`, `supersession`, `schema`, `related-entries` → `graph` | **child, not alias** |
| | `agent-rules`, `skill-architecture`, `lazy-loading` → `control-plane` | **child** |
| | `readme`, `functionality-audit`, `document-ingestion` → `documentation` | **child** |
| | `changelog`, `release-preflight` → `release` | **child** |
| | `merge`, `branch-history` → `git-workflow` | **child** |

Most of the 43 aliases in use are the second kind. That is not sloppiness — it is a flat schema
forcing a hierarchical vocabulary through the only field available.

**What the flattening costs.** Alias resolution maps child → parent and *discards the child*. An entry
authored `continuity` is read as `graph`, forever, with no way to recover that it was about continuity
specifically. Measured: **43 distinct aliases in use across 45 entries** are having their specificity
thrown away at read time. It also inflates the parents — part of why `graph` reads at 23.8% is that it
absorbs everything authored as `supersession`, `continuity`, `schema`, `related-entries` and `topics`.

## Design

**A slug may declare a `parent:`.** One parent, maximum depth 2 to start. `schema_version: 1 → 2`.

**Store the most specific slug; derive ancestors at read time.** An entry tagged `trail` is *also*
about `memory-trace`, but only `trail` is stored. Consequences:

- **The cap is unaffected** — it counts stored slugs, so a parent never consumes budget.
- **Search and filters expand downward.** Querying `memory-trace` matches `trail` entries. This is the
  same shape as the alias expansion `expand_topic_filter` already performs, so there is a natural home
  for it rather than a new mechanism.
- **No entry is rewritten.** The 197 entries carrying `memory-trace` are tagged at *parent* granularity
  — coarse, not wrong. Invariant #2 is untouched, and the corpus needs no migration.
- **A sweep can add a child later** to an entry carrying only the parent. That is enrichment against a
  gap, permitted under the `(source rank, then recency)` precedence rule without any retraction.

**Aliases keep exactly one job**: spelling variants of the same concept. Everything currently
mis-filed there becomes a child slug, which *recovers* specificity the corpus already recorded.

## Why this beats the flat splits

`topic-vocabulary-concentration-review.md` recommended carving `trail` out of `memory-trace` and
splitting `graph`. A hierarchy achieves the same specificity **without the two costs of a flat split**:

1. A flat split leaves `memory-trace` and its new sibling as unrelated peers, so the 197 historical
   entries become permanently unclassifiable at the finer grain — nothing connects the old label to the
   new one. Under a hierarchy they are simply parent-level.
2. A flat split forces a choice between breadth and specificity in one field. A hierarchy keeps both
   and lets each consumer pick its level.

So this **supersedes** the flat-split recommendation rather than competing with it.

## Communities — the reason this matters for the graph

Node colour today comes from **topics**, not topology (`graphCommunities.ts`). The topology route was
measured and closed: Louvain never merges across connected components, so on this corpus `k` is
floored at **110** and a ~16-slot legend is arithmetically unreachable
(`adr-graph-community-detection.md`, re-measured 2026-07-26).

Topic-derived communities have no such floor — they are *designed*, not discovered. But today they
inherit the concentration problem: three slugs (`memory-trace` 44.2%, `memory-seed` 24.2%, `graph`
23.8%) dominate the palette, so most of the map is three colours.

A hierarchy fixes this by **splitting the two jobs a community has to do**:

- **Parent → colour.** Few, stable, legible. A bounded palette that does not reshuffle as the corpus
  grows, because parents change rarely.
- **Child → grouping and filtering.** As specific as the vocabulary gets, without spending colours.

And it is what makes this work **at decision granularity**, which is JNL's point. A decision is a
smaller unit than an entry and should carry roughly one area and one activity — too small to justify a
colour of its own, but exactly the right size to sit inside a parent's colour. Per-decision child slugs
give the clustering; the parent gives the hue. That is a decision-level graph whose colouring is
legible and whose grouping is meaningful, which neither the flat vocabulary nor Louvain could deliver.

## Activities

JNL asked whether activities want the same treatment. **Partly — and for a different reason.**

The concentration review measured the activity axis as healthy: a graded distribution topping out at
21.3%, no slug swallowing the corpus. So hierarchy is **not** needed there to fix breadth.

But the alias evidence shows activities are losing specificity just as areas are: `documentation`
absorbs `readme` / `functionality-audit` / `document-ingestion`; `release` absorbs `changelog` /
`release-preflight`; `git-workflow` absorbs `merge` / `branch-history`. So apply the hierarchy to
activities for **specificity recovery**, not for concentration relief — and expect the tree to be
shallower and to matter less. Do areas first; treat activities as a follow-on that reuses the
mechanism.

## Build order

1. **`parent:` field, `schema_version: 2`, read-time ancestor derivation** in `load_topic_index` and
   `expand_topic_filter`. Nothing else changes behaviour yet.
2. **Reclassify** the aliases that are really children. This changes what 45 entries *resolve to* —
   strictly more specific, never contradictory — so re-measure facet counts before and after and
   record the delta.
3. **Point community colour at the parent level** and grouping/filtering at the child level.
4. **Only then** any topic sweep, so it judges against a vocabulary that can express the distinctions
   being asked for.

## Risks

- **Schema change touches every consumer** of the vocabulary: `topics check`, facets, the search
  filter, community colour, the swarm brief. Step 1 must be behaviour-neutral so the blast radius is
  visible before step 2 moves anything.
- **Two derivations risk.** Deriving the parent at read time is a second derivation of a displayed
  fact; the legend and node colour must both read it from **one** function, per the warning already in
  `graphCommunities.ts` — *"two derivations are how a legend ends up quietly lying."*
- **Depth discipline.** Two levels. Arbitrary depth invites a taxonomy nobody maintains, and the
  five-question test should be applied to any third level before it exists.
