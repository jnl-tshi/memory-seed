---
priority: P2
status: replaced
superseded_by: "../5_Completed/hierarchical-topic-vocabulary-proposal.md"
next_action: SUPERSEDED 2026-07-26 as to remedy - the measurements here stand, but the flat splits recommended below are replaced by `hierarchical-topic-vocabulary-proposal.md`, which achieves the same specificity without orphaning the 197 historical `memory-trace` entries from the finer grain. Read this document for the evidence; read that one for what to do.
---

# Topic vocabulary: concentration review

Measured 2026-07-26 over **446 topiced entries**, alias-resolved to canonical slugs. Prompted by JNL:
*"are there any topics which have too large a concentration, meaning that their description is too
broad… the goal is to be relatively specific about the subsystem and then relatively specific about
the activity."*

## Distribution

### Area axis (WHERE the work is)

| uses | share | slug | verdict |
|---:|---:|---|---|
| 197 | **44.2%** | `memory-trace` | **too broad — split** |
| 108 | 24.2% | `memory-seed` | residual by design (sharpened today); not a defect |
| 106 | **23.8%** | `graph` | **conflates two subsystems — split** |
| 52 | 11.7% | `session-logging` | healthy |
| 32 | 7.2% | `control-plane` | healthy |
| 19 | 4.3% | `mcp-tools` | healthy |
| 18 | 4.0% | `retrieval` | healthy |
| 13 | 2.9% | `mermaid` | healthy |
| 13 | 2.9% | `session-fuse` | healthy |
| 7 | 1.6% | `process-management` | thin |
| 7 | 1.6% | `windows-encoding` | thin (cross-cutting by design) |
| 5 | 1.1% | `session-layout` | thin |
| 5 | 1.1% | `hooks` | thin |

### Activity axis (WHAT was done)

| uses | share | slug |
|---:|---:|---|
| 95 | 21.3% | `ui-design` |
| 86 | 19.3% | `proposal-lifecycle` |
| 65 | 14.6% | `git-workflow` |
| 65 | 14.6% | `documentation` |
| 46 | 10.3% | `agent-collaboration` |
| 37 | 8.3% | `bugfix` |
| 20 | 4.5% | `release` |
| 10 | 2.2% | `tooling-evaluation` |
| 4 | 0.9% | `performance` |
| 1 | 0.2% | `security` |

The activity axis is **healthier** — a long, reasonably graded distribution with no slug above 22%.
It needs no structural change. The area axis is the problem.

## Finding 1 — `memory-trace` is a package, not a subsystem (44.2%)

Its description is *"The companion review UI package and its views"* — an entire application. A label
on nearly half the corpus carries almost no information, which is the same principle already written
into the inferred-topic cap: *a label applied to everything distinguishes nothing.*

Measured shape:

- 197 entries carry it
- 60 also carry `graph`
- **116 carry it as their ONLY area slug** — 26% of the whole corpus described by one undifferentiated label

Sampling those 116 shows at least four distinct subsystems inside the bucket: **Trail** (timeline,
git-graph rail, lane routing, relationship zone), **shell/chrome/layout** (sidebar, panes, collapse,
typography), **search UI**, and general app work.

That `graph` already exists as a peer slug is the proof this split works — graph was carved out of
memory-trace successfully and is now a legible area.

**Recommendation: carve out `trail`.** It is the highest-volume distinct surface, it is a named
product surface users talk about, and it is where most of the remaining volume sits. Chrome and
typography work is arguably already well described by `memory-trace` + activity `ui-design`, so a
separate shell slug is optional; start with `trail` and re-measure.

## Finding 2 — `graph` conflates a data model with a view (23.8%)

Description: *"Related-entry edges, lifecycle edges, continuity lineage, and graph schema"* — which is
the **data model**. But the slug is also used for the **Graph view** in Memory Trace. These live in
different packages.

| | n | sample |
|---|---:|---|
| `graph` **without** `memory-trace` | 46 | MCP link tools, evolves-edge proposal, `evolved_by` read-time constraint, F-file overlap ranking, continuity topics |
| `graph` **with** `memory-trace` | 60 | Trail git-graph timeline, force-directed layout, relationship lanes |

The first group is `memory_seed` core edge semantics; the second is rendering. Same slug, two
subsystems, and the split is nearly even — so neither reading can be called the dominant one.

**Recommendation: scope `graph` to the edge data model** (edges, lifecycle, continuity, schema —
matching its existing description) and give the visualisation its own slug. Under the split, a Graph
view entry would carry the view slug, and only carry `graph` as well when it genuinely touches edge
semantics.

## Finding 3 — a thin tail that has never distinguished anything

`security` (1 use), `performance` (4), `hooks` (5), `session-layout` (5), `tooling-evaluation` (10).

`security` and `performance` were added deliberately on 2026-07-19 as cross-cutting quality
attributes, and the decision-level-topics proposal already records them as *rare add-ons, not a third
axis* — so low counts are expected and correct there. `hooks` and `session-layout` are genuinely thin
areas; worth watching rather than acting on. **No recommendation to remove anything** — a slug used
rarely but precisely is not the same defect as a slug used constantly but vaguely.

## Why this must precede any topic sweep

Adding a narrower slug does **not** retroactively re-tag the 197 `memory-trace` entries; they keep
the broad label. What a sweep *can* do is **add** a narrower slug to an entry that already carries a
broad one — that is enrichment against a gap, not an override, so it is permitted under the
`(source rank, then recency)` precedence rule without any retraction.

So the ordering matters: split first, sweep second, and the sweep can carry the corpus forward.
Sweeping first would mint 933 judgments against a vocabulary that cannot express the distinctions
being asked for — which is precisely how the aborted pilot ended up measuring an ambiguity in
`memory-seed` rather than the swarm.

## What is NOT proposed

- No slug is removed or renamed. Renaming would orphan existing entries; the alias mechanism handles
  spelling, not meaning.
- No retroactive re-tagging. Invariant #2 forbids rewriting published entries, and the precedence rule
  forbids a derived value silently displacing a write-time one.
- No change to the activity axis. It is measurably healthy.
