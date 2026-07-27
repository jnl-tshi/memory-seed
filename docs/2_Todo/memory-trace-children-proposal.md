---
priority: P2
next_action: JNL to approve or reject the five candidate children. Nothing may be written to topics.yaml before that.
---

# Proposal: children for `memory-trace`

Status: **PROPOSAL — 2026-07-27, rewritten the same day.** The first run of proposal mode
(`scripts/propose_topic_children.py`), triggered by the concentration measurement as
[vocabulary-proposal-mode-proposal.md](vocabulary-proposal-mode-proposal.md) requires. No vocabulary
change has been made; `topics.yaml` is untouched.

> **The first version of this document reached the wrong conclusion, and it is corrected below rather
> than deleted.** It claimed that the 86 entries carrying `memory-trace` *and* a finer area slug were
> redundantly tagged, and that the fix was to retract the parent. JNL corrected it: `memory-trace`
> names the **subsystem** and the finer slug names the **component**, so the two are different facts,
> not a duplicate. The original conclusion also mis-read the measurement — see "What I measured wrong".

## What I measured wrong

`memory-trace` is on 202 of 461 topiced entries, 43.8%. I treated that as the problem. It is not: that
is the root's **reach**, and a subsystem root is *supposed* to reach a large share of the work.

The number a hierarchy actually deflates is the **canonical** count — entries that land ON the root
because nothing more specific exists. `measure_topic_concentration.py` prints both columns and says so
in its own docstring; I read the wrong one. Today the two are identical (202 / 202) for exactly one
reason: `memory-trace` has no children, so every entry has nowhere else to land.

**Reach is preserved by derivation, not by tagging.** Store the most specific slug and the ancestors
follow — `ancestors()` walks up, `expand_topic_filter` expands down. Filtering on `memory-trace` still
finds all 202 after a split. That is the whole point of the hierarchy, and it is why nothing needs to
be retracted for concentration to fall.

## Projection under the corrected framing

Each entry authoring only its deepest area slug:

| | entries | share |
|---|---|---|
| `memory-trace` **reach** (rollup) | 202 | unchanged |
| `memory-trace` **canonical**, today | 202 | 43.8% |
| `memory-trace` **canonical**, with the children below | **~49** | **10.6%** |

## Candidates

Axis `area`, matching the parent — a child never crosses axes. Counts are entries where the candidate's
subject matter is what the entry is about.

| candidate | entries | what it covers |
|---|---|---|
| **`graph-view`** | 63 | the relationship map: orphans, node sizing, community colour, force motion, decision rows |
| **`trail`** | 40 | the chronological timeline: decision rows, lanes, brackets, group anchors |
| **`trace-ui`** | 14 | the app frame: settings, panes, docking, typography, theme, find bar |
| **`trace-cache`** | 12 | startup, incremental derivation, freshness, generation, rebuild |
| **`trace-harness`** | 10 | Storybook, Playwright, e2e, a11y gates, renderer evidence |
| `inspector` | 7 | the entry reader pane — **below the floor of 8**, revisit |
| `diagram-view` | 4 | the Mermaid viewer — below floor |
| `trace-api` | 3 | versioned contract, projection payloads — below floor |

### `graph-view` exists because `graph` is doing two jobs

The first version declined this child on the grounds that the `graph` root already covered the seam.
The corpus says otherwise — `graph` currently spans two subsystems:

- **63 entries** carry `graph` *with* `memory-trace`: the Trace graph **view** — "Graph orphans: edge
  ceiling", "Size graph nodes by degree centrality", "Continuous whole-graph physics".
- **45 entries** carry `graph` *without* it: the Seed **edge model** — "Draft evolution-edges
  proposal", "Replace core topics with structured continuity field", "Complete MCP sidecar-edge
  parity".

Those are different areas that happen to share a word. `graph`'s existing children (`continuity`,
`related-entries`, `schema`, `supersession`) are all data-model concepts, which confirms where that
slug's centre of gravity is: the Seed side. A Trace `graph-view` child would take rendering concerns,
and its own grandchildren — if it ever earns them — would be rendering concerns too.

**`graph` therefore has a concentration problem of its own**, and it is the next item in the work
queue, not part of this proposal.

## Under-floor candidates

`inspector` (7), `diagram-view` (4) and `trace-api` (3) are real distinctions that have not yet earned
a slug. The floor is what separates earned depth from a vocabulary that grows whenever someone wants a
finer label. `inspector` is one entry short and will likely qualify on its own within a week of
inspector work.

## Retraction: narrow, and not this

**Settled 2026-07-27 by JNL.** A topic retraction mechanism is worth having, scoped to **corrections** —
a topic that is genuinely wrong, or a `derived` block correcting a `write-time` one, which
[sidecar-supersession-model.md](../3_Spec/draft/sidecar-supersession-model.md) already identifies as
having no legal spelling today.

It is explicitly **not** the instrument for deflating a parent. Depth does that, by derivation, without
touching anything an author wrote. Reaching for retraction to fix concentration would mean deleting
true statements to make a number smaller.

## Cycle 3: two independent swarms, and the numbers that stand

**Settled 2026-07-27 by JNL:** the axes are judged by SEPARATE swarms so each recommends independently
from the same material. Three cycles ran; the counts below are cycle 3's.

| area answer | entries |
|---|---|
| `trail` | 32 |
| **`TRACE-WIDE`** (the app frame — no child, stays on the root) | 26 |
| `NONE` (roadmap, release, git housekeeping) | 17 |
| `trace-cache` | 12 |
| `trace-harness` | 8 |
| `graph` (single-area; +63 dual-tagged = **70**) | 7 |
| `seed-other` / `lifecycle-edges` | 6 |
| `diagram-view` | 4 |
| `trace-api` | 2 |
| `inspector` | 1 |

Neither area worker proposed a new child; both checked explicitly and declined `find-bar` (3) and a
`lifecycle-edges` child (3) on the floor. After three cycles the area set has stopped moving.

**The activity swarm scored 0.89 against first-hand authored tags** (85 of 95 entries whose author wrote
an activity slug). The aborted pilot scored 0.583 asking one worker for ~2 slugs from 23 across both
axes at once. Separating the axes is what moved it — an easier, better-defined question, not a lowered
gate. 20 further entries carry no authored activity at all, where the swarm adds rather than checks.

### What the split-swarm design exposed: the activity axis is missing `testing`

The area swarm has a home for harness work (`trace-harness`, 8 entries). The activity swarm does not —
so Storybook, Playwright and CI wiring were filed as **`ui-design`**, with one worker reasoning they
were "reasonably subsumed" there. Building a test harness is not design work; the vocabulary simply has
nowhere else to put it.

Neither activity worker proposed it, because each saw only half the corpus and the category clears the
floor only when pooled. **Proposal detection has to run over the combined result, not per worker** — a
protocol fix for the sweep, not a one-off.

## What is being asked

**Approve or reject the children that clear the floor**: `graph` (70), `trail` (32), `trace-cache` (12),
and `trace-harness` (8, exactly at the floor). `trace-ui` is WITHDRAWN — it was an area slug for what the
activity axis already says, and 77% of its entries already carried `ui-design`; that work is `TRACE-WIDE`
and stays on the root. `inspector` (1) and `diagram-view` (4) remain below the floor.

Separately: **`lifecycle-edges`** under `memory-seed` (approved 2026-07-27) takes the 45 Seed-side edge
entries plus `graph`'s four existing children, so `graph` can become a Trace child without dragging Seed
work under it. And an ACTIVITY slug for test/verification work is now evidenced at 8 entries. Approval means adding five `parent: memory-trace` slugs to
`topics.yaml` — a governance change to deploy-once state, which an agent cannot make.

Nothing else is required. No entry is rewritten, no topic is removed, and the parent keeps its full
reach.

## Notes for whoever picks this up

- Clustering was keyword-led over entry titles and then reviewed, not a swarm pass over the bodies.
  That is weaker evidence than the design asks for: 26 of the 116 single-area entries matched no
  pattern, and those boundaries are the ones a swarm would firm up.
- Re-run any number here with:
  `python scripts/measure_topic_concentration.py`
  `python scripts/propose_topic_children.py gather memory-trace`
  `python scripts/propose_topic_children.py score memory-trace <split.json>`
- The scorer's floor and target are stated in code (`MIN_CHILD_ENTRIES`, `TARGET_PARENT_SHARE`). It
  scores the *canonical* residual, so re-running it after this reframe requires the split to include
  `graph-view` — without that child it still reports REJECT, correctly.
