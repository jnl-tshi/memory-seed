---
priority: P2
next_action: JNL to rule on the table in "The ask" - three slugs are measurement-backed and ready, six are argued but unmeasured, and one (trace-harness) fails the floor by one entry and needs a call. Nothing may be written to topics.yaml before that.
---

# Proposal: the topic vocabulary change

Status: **PROPOSAL — 2026-07-27, consolidated the same evening.** Triggered by the concentration
measurement as [vocabulary-proposal-mode-proposal.md](vocabulary-proposal-mode-proposal.md) requires.
No vocabulary change has been made; `topics.yaml` is untouched.

> **The filename says `memory-trace-children` and the scope outgrew it.** The ask now also covers a
> child under `memory-seed`, a new root, and two activity slugs. The file keeps its name so inbound
> links and the docs index stay valid; the title is the accurate one.

## The ask

One table. Every row is a slug to add to `.memory-seed/topics.yaml`; nothing else is requested, no
entry is rewritten, no topic is removed, and every parent keeps its full reach by derivation.

**The `evidence` column is the point.** These rows are not equally well supported, and the previous
version of this document presented them as if they were.

| slug | parent | axis | count | evidence | admitted by | ready? |
|---|---|---|---:|---|---|---|
| `graph` | `memory-trace` | area | **70** | two blind workers agreed, + 64 dual-tagged | floor (≥8) | **yes** |
| `trail` | `memory-trace` | area | **30** | two blind workers agreed | floor (≥8) | **yes** |
| `trace-cache` | `memory-trace` | area | **12** | two blind workers agreed | floor (≥8) | **yes** |
| `trace-harness` | `memory-trace` | area | **7** | agreed count; w1 said 9, w2 said 7 | **FAILS floor by 1** | **needs your call** |
| `panes` | `memory-trace` | area | ~23 | keyword estimate, never put to a swarm | floor (≥8) — plausibly, unverified | no |
| `inspector` | `panes` | area | 1–40 | swarm 1, keyword ~40 — see below | no floor at gen 3 | no |
| `topbar` | `panes` | area | ~17 | keyword estimate | no floor at gen 3 | no |
| `navigation` | `panes` | area | ~14 | keyword estimate | no floor at gen 3 | no |
| `settings` | `panes` | area | ~14 | keyword estimate | no floor at gen 3 | no |
| `workspace-bar` | `panes` | area | ~11 | keyword estimate | no floor at gen 3 | no |
| `diagram-view` | `panes` | area | 4 | two blind workers agreed | no floor at gen 3 | no |
| `lifecycle-edges` | `memory-seed` | area | ~45 | your ruling + `graph`'s 4 existing children | floor (≥8) | you already approved it |
| `package` | *(root)* | area | ~66 | your ruling from adjudication row 3 | root, no floor | no |
| `feature-build` | *(root)* | activity | ~116 | your ruling; the axis had no verb for BUILDING | root, no floor | no |
| `testing` | *(root)* | activity | ~8 | the split-swarm mismatch, pooled across workers | root, no floor | no |

**Three rows are ready now**, and they are the three that carry the concentration. Approving only
those takes `memory-trace` canonical from 43.2% to **16.7%**, under the 20% target, which is the
entire problem this was triggered by. Everything else can wait for evidence without blocking it.

Two things the table cannot show:

- **`graph` and `lifecycle-edges` are one move, not two.** `graph` cannot be reparented under
  `memory-trace` while 45 of its entries are Seed-side edge-model work — that would be the
  ancestor-fit violation rule 3 forbids. `lifecycle-edges` is what takes them. Approving `graph`
  without it would file 45 entries under a subsystem they have nothing to do with.
- **`trace-api` is deliberately not in the table.** 1 agreed entry, no grouping parent, and unlike
  `trace-harness` nobody has argued for it. It stays on the root.

### The rules each row is admitted by

From [hierarchical-topic-vocabulary-proposal.md](hierarchical-topic-vocabulary-proposal.md), settled
2026-07-27:

1. **Levels must be well bounded** — a child earns its place by being distinguishable without
   judgement. The `panes` children qualify on this one strongly: each names a DOM region, so two
   siblings cannot overlap.
2. **The floor applies to generation 2 only** — `MIN_CHILD_ENTRIES = 8` decides whether a new BRANCH
   is justified. Below that there is no floor, which is why the six pane children need no count and
   `panes` itself does.
3. **A slug must fit every ancestor** — the constraint that pays for rule 2, and a worker rule rather
   than a vocabulary rule.

### The live run behind the "yes" rows

Reproduce with:

```bash
python scripts/tally_swarm_area.py . --out split.json && python scripts/propose_topic_children.py score memory-trace split.json
```

```
entries carrying memory-trace : 204
judged by both workers        : 116
agreed                        : 107  (92%)

parent memory-trace: 204 entries, 43.2% of 472
proposed children are generation 2 - floor of 8 applies

  graph                            70 entries  14.8% of corpus   ok
  trace-cache                      12 entries   2.5% of corpus   ok
  trace-harness                     7 entries   1.5% of corpus   UNDER FLOOR (8)
  trail                            30 entries   6.4% of corpus   ok

  (residual on the parent)         79 entries  16.7% of corpus
```

The tally script quotes the **agreed** column — the label both blind workers reached independently —
because a count one worker reached is a hypothesis. That choice is what exposes the `trace-harness`
problem, and it is why the numbers here are slightly lower than the ones this document carried
earlier.

### The one thing that needs a decision, not more evidence

**`trace-harness` is 9 by worker 1, 7 by worker 2, 7 agreed.** It clears the floor on one reading and
fails on the other, and it has no natural parent to sit under — it is not a pane. So the scorer's
usual remedy ("propose it under a grouping child") does not apply. Three options:

- **Wait.** It stays on the root until it reaches 8 agreed. Costs nothing; CI work will get it there.
- **Approve at 7**, on the grounds that the floor is a guard against unearned depth and a
  one-entry miss on a category with a Storybook directory behind it is not that.
- **Fold it into `panes`** — rejected here: a test harness is not a pane, and stretching `panes` to
  hold it would break rule 1, which is the rule that makes the pane set worth having.

I would wait. But it is a judgement call about your own vocabulary, which is why it is listed rather
than decided.

### What is NOT measured, stated plainly

- **The pane split has never been run over the population.** The swarm judged 116 entries against a
  vocabulary with no pane labels, so `topbar`, `navigation`, `settings` and `workspace-bar` have
  keyword estimates only. The evidence for them is the DOM boundary (rule 1) plus a re-ruling of 22
  adjudicated rows, where naming the panes moved three of six entries off `TRACE-WIDE`. That is a good
  argument and a small sample.
- **`panes` itself is therefore unverified at the floor.** It needs ≥8 of the 79-entry residual, and
  the 23 entries both workers called `TRACE-WIDE` are where they would come from. Plausible, unproven.
- **`inspector` is the count I would not act on blindly.** The swarm said **1**; the keyword estimate
  says **~40**. They answer different questions — *what is this entry about* versus *which pane did it
  touch* — and only the first supports a slug. Display panes get touched by everything.
- **`package`, `settings` and `feature-build` are keyword estimates** over titles and bodies. That is
  the same method that put `trail` at 40 where the swarm found 30. Order-of-magnitude only.

**The obvious way to close all four gaps at once** is one area swarm pass over the 79-entry residual
with the pane vocabulary in hand. That is a measurement, not a rewrite, and nothing about the three
ready rows depends on it.

---

*Everything below is the reasoning and the record. The ask is above.*

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
|---|---:|---:|
| `memory-trace` **reach** (rollup) | 204 | unchanged, always |
| `memory-trace` **canonical**, today | 204 | 43.2% |
| `memory-trace` **canonical**, with the three ready children | **79** | **16.7%** |

> The **~49 / 10.6%** this row claimed earlier assumed every candidate landed, including the pane split
> and `trace-harness`. The 79 above is what the three measurement-backed children alone deliver, and it
> is a live scorer figure rather than a projection — see "The live run behind the yes rows". It already
> clears the 20% target, which is why the unmeasured rows do not block anything.

## Candidates — SUPERSEDED, kept as the record

> **Do not read counts off this table.** It is the first run, before the axes were split and before the
> panes were named. `trace-ui` was withdrawn (an area slug for what the activity axis already says) and
> `graph-view` was folded back into `graph` once `lifecycle-edges` gave the Seed-side edge work its own
> home. The live numbers are in "The ask".

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

### `graph` is doing two jobs — the measurement that made `lifecycle-edges` necessary

This was the argument for a separate `graph-view` slug. The measurement stands; the conclusion drawn
from it changed. `graph` spans two subsystems:

- **64 entries** carry `graph` *with* `memory-trace`: the Trace graph **view** — "Graph orphans: edge
  ceiling", "Size graph nodes by degree centrality", "Continuous whole-graph physics".
- **45 entries** carry `graph` *without* it: the Seed **edge model** — "Draft evolution-edges
  proposal", "Replace core topics with structured continuity field", "Complete MCP sidecar-edge
  parity".

Those are different areas that happen to share a word. `graph`'s existing children (`continuity`,
`related-entries`, `schema`, `supersession`) are all data-model concepts, which confirms where that
slug's centre of gravity sits: the Seed side.

**A new `graph-view` slug was the wrong fix**, because it leaves the ambiguous word on the Seed half
where the ambiguity actually lives. `lifecycle-edges` is the right one: it names the Seed edge-model
work explicitly, takes the four existing children with it, and frees `graph` to mean the Trace view —
no new slug for the 64 rendering entries, and no entry filed under a parent it does not belong to.

## Under-floor candidates — resolved by the generation rule

This section originally rejected `inspector`, `diagram-view` and `trace-api` for want of 8 entries. The
floor rule settled later the same day makes most of that moot: it applies to **generation 2 only**, so
`inspector` and `diagram-view` are admissible as grandchildren under `panes` regardless of count.

What survives is `trace-api` (1 agreed), which has no grouping parent — the same position
`trace-harness` is in, and the same open call.

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
from the same material. Three cycles ran; the counts below are cycle 3's, re-derived 2026-07-27 evening
from the saved worker answers with `scripts/tally_swarm_area.py`.

Both workers judged all 116 entries blind to each other. **Agreement 107/116 = 92%.**

| area answer | worker 1 | worker 2 | **agreed** |
|---|---:|---:|---:|
| `trail` | 32 | 32 | **30** |
| **`TRACE-WIDE`** (no child fits; stays on the root) | 25 | 25 | **23** |
| `NONE` (roadmap, release, git housekeeping) | 18 | 21 | **18** |
| `trace-cache` | 13 | 12 | **12** |
| `trace-harness` | 9 | 7 | **7** |
| `graph` (single-area; +64 dual-tagged = **70**) | 8 | 6 | **6** |
| `diagram-view` | 4 | 4 | **4** |
| `seed-other` | 3 | 3 | **3** |
| `lifecycle-edges` | 2 | 2 | **2** |
| `trace-api` | 1 | 3 | **1** |
| `inspector` | 1 | 1 | **1** |

> **This table replaces the figures this document carried earlier** (`TRACE-WIDE` 26, `NONE` 17,
> `trace-harness` 8, `trace-api` 2). Those were not reproducible from either worker file or from any
> stated rule for combining them — they appear to have been read off a live result that was never
> saved. The counts here come from the committed TSVs and a stated rule: **quote the agreed column.**
>
> It is not a cosmetic correction. `trace-harness` was the row presented as "8, exactly at the floor",
> and on the agreed reading it is **7 and fails** — which is now the one open decision in the ask.

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

## Where the pane set came from (2026-07-27)

The reasoning behind the `panes` rows in "The ask". This is not a second ask — the table at the top is
the only one.

### AREA — the panes

**Every pane is named** (JNL, 2026-07-27), so no surface is homeless and `TRACE-WIDE` can mean only what
is genuinely cross-cutting. The slugs come from the app's real regions, not from invented groupings —
which is what makes them satisfy rule 1: a change is in one `<aside>` or another, so two siblings cannot
overlap. No definition written by hand carries that guarantee, and reading the component tree is what
caught my two errors: I had proposed `context`, which is a SECTION inside the navigation pane, and had
missed `topbar` and `workspace-bar` entirely.

**`panes` is their parent** (JNL, 2026-07-27) — *"filtering by panes should still allow me to see
anything tagged with any of the children thanks to the hierarchy."* It costs one slug and buys the
option; the six children then sit at generation 3 where no floor applies, which is what makes
`inspector` (1) and `diagram-view` (4) admissible at all.

| slug | the region it names | keyword est. | |
|---|---|---|---|
| `graph` | `GraphWorkspace` — the relationship map | 146 | not a pane; a workspace, and reparented from root |
| `trail` | `TrailWorkspace` — the timeline | 133 | not a pane; a workspace |
| `panes` | the grouping parent for the six below | ~23 | |
| `inspector` | `<aside class="inspector">` — the reader | ~40 | |
| `topbar` | `<header class="topbar">` — search, view switch, worktree picker, refresh | ~17 | |
| `navigation` | `<aside class="navigation-pane">` — project, topics, context list | ~14 | replaces the earlier `context`, which was a SECTION inside it |
| `settings` | `SettingsMenu.tsx` | ~14 | |
| `workspace-bar` | scope / range / labels / edge filters | ~11 | |
| `diagram-view` | `DiagramViewer.tsx` | 4 | the only pane child with a swarm-agreed count |
| `trace-cache` | startup, caching, freshness, worktree switching | 12 | not a pane |
| `trace-harness` | Storybook, Playwright, e2e, CI wiring | 7 | not a pane; **one short of the floor** |

**These counts are upper bounds.** They come from keyword presence over titles and bodies, so `trail`
133 and `graph` 146 against 204 memory-trace entries means most entries MENTION both. The swarm's
stricter "what is this entry about" reading gave `trail` **30** and `graph` 70. What the keyword numbers
establish is that each pane is nameable and non-trivial — not that each owns that many entries.

**What naming every pane did to `TRACE-WIDE`:** re-ruling the 22 adjudicated rows with the full set
moved three of six off it, all to `topbar` (search routing, full-text navigation, the unified find bar).
`TRACE-WIDE` now holds three: a package-wide module rename, a multi-pane design pass, and a loading
mechanism JNL ruled wide-impact. That is what the answer should mean — cross-cutting, not homeless.

### AREA — elsewhere

| slug | entries | evidence |
|---|---|---|
| `lifecycle-edges` under `memory-seed` | ~45 | takes `graph`'s four current children, which are all edge-MODEL concepts |
| `package` (root) | ~66 | JNL, from adjudicating row 3; spans Seed and Trace, currently homeless |

### ACTIVITY

| slug | entries | evidence |
|---|---|---|
| `feature-build` | **~116 (25% of the corpus)** | JNL. The axis had slugs for fixing, designing, documenting, proposing, merging and shipping — and none for BUILDING. `ui-design` had been absorbing it for UI work, which is why the gap only surfaced on a backend row |
| `testing` | ~8 | the split-swarm mismatch: the area axis had `trace-harness`, the activity axis had nowhere, so Storybook and Playwright were filed as `ui-design` |

### The rule that separates `feature-build` from `ui-design`

> **`feature-build`** — a capability that did not exist before.
> **`ui-design`** — changing how an existing thing looks or behaves.

Applied across the 22 adjudicated rows this moved six of them and took `ui-design` from 9 to 4. If the
line belongs elsewhere, those six move together — it is one decision, not six.

*(The open questions that used to be listed here are now in "What is NOT measured" at the top, with the
counts corrected against the saved worker answers.)*

## Why `lifecycle-edges` has to land with `graph`

`graph` cannot become a child of `memory-trace` on its own, because 45 of the entries carrying it are
Seed-side edge-model work — "Draft evolution-edges proposal", "Replace core topics with structured
continuity field" — and filing those under Memory Trace would be exactly the ancestor-fit violation
rule 3 forbids. `lifecycle-edges` under `memory-seed` takes them, along with `graph`'s four existing
children (`continuity`, `related-entries`, `schema`, `supersession`), which are all data-model concepts
and confirm where that slug's centre of gravity sits.

So the two are one move, not two: **`lifecycle-edges` is what makes `graph` safe to reparent.**

## Notes for whoever picks this up

- **The counts in "The ask" are re-derivable; the ones in the superseded sections are not.**
  `scripts/tally_swarm_area.py` reads the saved worker answers and prints all three columns (w1, w2,
  agreed) so the conservative choice is visible rather than asserted.
- Do not `cat` the swarm TSVs together. `B_area1.tsv` has no trailing newline, so concatenation glues
  its last record to the first record of the next file and silently corrupts both. The tally script
  reads them line-by-line and says so in a comment.
- Clustering for the unmeasured rows was keyword-led over entry titles and then reviewed, not a swarm
  pass over the bodies. 26 of the 116 single-area entries matched no pattern, and those boundaries are
  the ones a swarm would firm up.
- Re-run everything with:
  `python scripts/measure_topic_concentration.py`
  `python scripts/tally_swarm_area.py . --out split.json`
  `python scripts/propose_topic_children.py score memory-trace split.json`
- The scorer's floor and target are stated in code (`MIN_CHILD_ENTRIES`, `TARGET_PARENT_SHARE`), and it
  scores the *canonical* residual, not reach.
