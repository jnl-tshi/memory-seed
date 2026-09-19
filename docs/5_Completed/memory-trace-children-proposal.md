---
completed_on: "2026-09-19"
completion_note: "The approved topic changes and attribution pass shipped; residual evaluation is carried by the hosted MVP programme."
priority: P2
next_action: DONE 2026-07-27 - 17 slugs live in .memory-seed/topics.yaml and 166 entries attributed via topic sidecars. Reparenting `graph` is WITHDRAWN, not deferred: it would add 0 true positives and 45 false ones, so no mechanism makes it worthwhile. Remaining open items are the activity axis (no swarm pass yet, `feature-build` unverified at ~116) and validity, still 74% held-out.
---

# Proposal: the topic vocabulary change

Status: **PROPOSAL — 2026-07-27, consolidated the same evening.** Triggered by the concentration
measurement as [vocabulary-proposal-mode-proposal.md](../5_Completed/vocabulary-proposal-mode-proposal.md) requires.
No vocabulary change has been made; `topics.yaml` is untouched.

> **The filename says `memory-trace-children` and the scope outgrew it.** The ask now also covers a
> child under `memory-seed`, a new root, and two activity slugs. The file keeps its name so inbound
> links and the docs index stay valid; the title is the accurate one.

## APPROVED AND APPLIED — 2026-07-27

JNL approved. **17 slugs are live in `.memory-seed/topics.yaml`**, no entry was rewritten, no topic was
removed, and every existing filter returns exactly what it returned before.

| what landed | slugs |
|---|---|
| under `memory-trace` | `trail`, `trace-cache`, `trace-harness`, `panes` |
| under `panes` | `topbar`, `navigation`, `inspector`, `diagram-view` |
| new area roots | `lifecycle-edges`, `topic-vocabulary`, `test-suite`, `docs-lifecycle`, `package` |
| new activity roots | `feature-build`, `testing` |
| renamed | `memory-seed` → **`seed-core`** (old name kept as an alias) |
| reparented | `continuity`, `related-entries`, `schema`, `supersession`: `graph` → `lifecycle-edges` |
| **declined** | `settings`, `workspace-bar` — zero agreed entries each |

**Two decisions were taken at apply time and both are reversible one line at a time.**

**1. The four Seed areas are ROOTS, not children of `seed-core`** (JNL's ruling). `topics.yaml` declares
the old `memory-seed` slug a RESIDUAL area — *"a residual area takes no children by definition: anything
specific enough to name is by construction not residual"* — and its peers `graph`, `retrieval`,
`session-logging`, `mcp-tools` are all roots already. Making the four children would have contradicted
that rule; making them roots keeps it, and the swarm had just measured the rule holding (34 of 39
declined entries belonged to a *different existing root*). The rename follows: `memory-seed` read like
the whole package, which is what a residual must not read like, and is why it had collected 127 entries.

Consequence to be aware of: filtering `seed-core` no longer reaches the four areas. Under the residual
reading that is correct — those entries were never *about* the residual, they were parked there.

**2. Reparenting `graph` under `memory-trace` is WITHDRAWN — not deferred.**

I first reported this as blocked pending a reassignment campaign, and that was wrong. Three reasons, in
order of how long each stays true:

**It has no upside.** 64 entries carry `graph` *with* `memory-trace`; 45 carry it *without*. The 64
already reach `memory-trace` directly, so reparenting adds **0 true positives and 45 false ones** — a
filter returning 249 rows instead of 204, an 18% false-positive rate, pulling in "Draft evolution-edges
proposal" and "Replace core topics with structured continuity field". That is arithmetic. No future
mechanism changes it, which is why the reassignment campaign was never the answer.

**Topic retraction does not exist.** Moving the 45 would need a derived block overriding an authored
slug. [sidecar-supersession-model.md](../3_Spec/draft/sidecar-supersession-model.md) specs that as
*"step 1 of the consolidation build order"* and nothing implements it;
`augment_chunks_with_topic_sidecars` deliberately does not union into `chunk.topics`, so a sidecar
cannot un-say an authored topic.

**It would fail the retraction rule anyway.** JNL, 2026-07-27: *"a retraction should be judgeable as
'was this claim wrong?'. If the answer is 'no, it was true but I would rather it were more specific',
the answer is a child slug, not a retract."* `graph` on "Draft evolution-edges proposal" was **true** —
the Seed edge model *is* the graph's data model. This is the 86-entry parent-retraction trap wearing a
new costume.

What remains true is that `graph` names two things. That is now recorded rather than fixed:
`lifecycle-edges` gives the Seed edge model its own root and took the four data-model children, so new
work has somewhere specific to go. The historical dual meaning stays, because every one of those tags
was true when written. `graph-view` is **not** being resurrected — it would be a slug with zero authored
entries and zero swarm evidence, the case `settings` and `workspace-bar` were declined for.

## The attribution campaign — 166 entries, applied 2026-07-27

The swarm's agreed labels are now written as **topic sidecars**, the first in this repo:
`.memory-seed/sessions/topics/YYYY-MM/YYYY-MM-DD.md`, 18 files, one block per entry filed under the
entry's own date.

| slug | entries | | slug | entries |
|---|---:|---|---|---:|
| `trail` | 34 | | `docs-lifecycle` | 11 |
| `lifecycle-edges` | 34 | | `graph` | 7 |
| `topic-vocabulary` | 25 | | `diagram-view` | 6 |
| `trace-cache` | 14 | | `panes` | 5 |
| `trace-harness` | 12 | | `topbar` | 4 |
| `test-suite` | 12 | | `inspector` | 2 |
| | | | `navigation` | 1 |

**This is enrichment, not correction.** No authored topic is touched, contradicted or removed — the
sidecar is a separate `inferred_topics` channel beside what the author wrote. Every entry that had a
coarse area slug keeps it and gains a specific one.

**What was filtered out before writing**, rather than left for the validator to catch: the ballot
options `NONE` (46), `TRACE-WIDE` (35), `OTHER-ROOT` (34) and `SEED-WIDE` (5) are answers, not slugs;
`seed-other` (3) and `trace-api` (1) are not canonical and `trace-api` was explicitly declined. The 21
rows where the two workers disagreed get no sidecar at all.

**A footgun for the next campaign:** `entry_topic_sidecars` is **most-recent-wins per entry, wholesale**
— a topic list is a state replaced by a better one, not a set that unions. These blocks carry one area
slug and no activity. An activity-axis campaign writing sidecars for the same entries will **replace**
these entirely, not merge with them. It must carry the area slug forward in the same block.

**On the `topic_swarm.md` STOP notice:** it aborts the **decision-level** `<slug>:dN` backfill — 933
judgment units against a 0.70 roll-up-recall gate. This campaign is entry-level area attribution from an
already-run swarm at 92–94% agreement, under the separated-axis premise the STOP explicitly asks for
(*"reviving this campaign requires a changed premise"*). Different unit, different gate, different
premise — stated here so it is not later read as a bypass.

One quirk worth knowing: `topics check` still reports these slugs as `unused-topic`, because that rule
counts **authored** topics only and does not see the sidecar channel. 166 entries carry them.

*The ask that was approved is preserved below.*

## The ask

One table. Every row is a slug to add to `.memory-seed/topics.yaml`; nothing else is requested, no
entry is rewritten, no topic is removed, and every parent keeps its full reach by derivation.

**The `evidence` column is the point.** These rows are not equally well supported, and the previous
version of this document presented them as if they were.

Every count below is now **swarm-measured** — two workers judging blind, and only labels they reached
independently are counted. Cycle 4 (2026-07-27) covered the last unjudged material, so no row rests on
a keyword estimate any more.

| slug | parent | axis | count | evidence | admitted by | ready? |
|---|---|---|---:|---|---|---|
| `graph` | `memory-trace` | area | **70** | agreed, + 64 dual-tagged | floor (≥5) | **yes** |
| `trail` | `memory-trace` | area | **34** | agreed | floor (≥5) | **yes** |
| `trace-cache` | `memory-trace` | area | **14** | agreed | floor (≥5) | **yes** |
| `trace-harness` | `memory-trace` | area | **12** | agreed | floor (≥5) | **yes** |
| `panes` | `memory-trace` | area | **13** | agreed — 5 as a multi-pane label, 8 in its children | floor (≥5) | **yes** |
| `topbar` | `panes` | area | **4** | agreed (keyword estimate said ~17) | no floor at gen 3 | **yes** |
| `diagram-view` | `panes` | area | **2** | agreed | no floor at gen 3 | **yes** |
| `inspector` | `panes` | area | **1** | agreed (keyword estimate said ~40) | no floor at gen 3 | your call |
| `navigation` | `panes` | area | **1** | agreed (keyword estimate said ~14) | no floor at gen 3 | your call |
| `settings` | `panes` | area | **0** | **neither worker placed a single entry here** | no floor at gen 3 | **no** |
| `workspace-bar` | `panes` | area | **0** | **neither worker placed a single entry here** | no floor at gen 3 | **no** |
| `lifecycle-edges` | `memory-seed` | area | **32** here, **63** with the Seed-side `graph` set | agreed | floor (≥5) | **yes**, and you already approved it |
| `topic-vocabulary` | `memory-seed` | area | **25** | agreed | floor (≥5) | **yes** |
| `test-suite` | `memory-seed` | area | **12** | agreed | floor (≥5) | **yes** |
| `docs-lifecycle` | `memory-seed` | area | **11** | agreed | floor (≥5) | **yes** |
| `package` | *(root)* | area | ~66 | your ruling from adjudication row 3 | root, no floor | not measured |
| `feature-build` | *(root)* | activity | ~116 | your ruling; the axis had no verb for BUILDING | root, no floor | not measured |
| `testing` | *(root)* | activity | ~8 | the split-swarm mismatch, pooled across workers | root, no floor | not measured |

**Both roots clear the target, and both splits score ACCEPTABLE:**

| root | canonical today | with its ready children | target |
|---|---:|---:|---|
| `memory-trace` | 42.9% | **12.8%** | ≤20% ✔ |
| `memory-seed` | 26.7% | **9.9%** | ≤20% ✔ |

**The thing to decide is no longer whether the children are real — it is how many pane children to
create.** `panes` earns its place at 13. Four of its six proposed children came back at 4, 2, 1 and 1;
the other two came back at **zero**. Details in "What cycle 4 changed".

> **The floor moved from 8 to 5 (JNL, 2026-07-27)**, which is what made `trace-harness` the fourth ready
> row instead of an open question. The reasoning is in
> [hierarchical-topic-vocabulary-proposal.md](hierarchical-topic-vocabulary-proposal.md) rule 2: 8 was
> set before the generation rule existed, when this one constant carried the whole depth question, and
> it is now doing a much narrower job.

Three things the table cannot show:

- **`graph` and `lifecycle-edges` are one move, not two.** `graph` cannot be reparented under
  `memory-trace` while 45 of its entries are Seed-side edge-model work — that would be the
  ancestor-fit violation rule 3 forbids. `lifecycle-edges` is what takes them. Approving `graph`
  without it would file 45 entries under a subsystem they have nothing to do with.
- **`lifecycle-edges` is 63, not the ~45 this document said earlier.** Two sets were being counted
  separately: 45 entries carry `graph` without `memory-trace` (the Seed-side edge model), and 35 carry
  `memory-seed` and are edge work. They overlap on **17**, so the union is **63** — 13.3% of the corpus,
  and the second-largest slug in the whole ask after `graph`. It is big enough to earn grandchildren
  immediately: the ~14 `Cycle N` link-campaign entries are an obvious `link-swarm`, and at generation 3
  no floor applies to them.
- **`trace-api` is deliberately not in the table.** 1 agreed entry, no grouping parent, and unlike
  `trace-harness` nobody has argued for it. It stays on the root.

### What cycle 4 changed

Two blind haiku workers judged the 79-entry `memory-trace` residual against the full pane vocabulary,
and all 127 `memory-seed` entries against the four proposed children. Raw answers:
`docs/4_Reference/topic-swarm-cycles/cycle4-*.tsv`.

**1. The pane children collapsed, and by an order of magnitude.** The keyword estimates were measuring
*which pane a change touched*; the swarm was asked *what the entry is about*. Only one of those supports
a slug:

| pane | keyword estimate | swarm-agreed |
|---|---:|---:|
| `inspector` | ~40 | **1** |
| `topbar` | ~17 | **4** |
| `navigation` | ~14 | **1** |
| `settings` | ~14 | **0** |
| `workspace-bar` | ~11 | **0** |
| `diagram-view` | ~4 | **2** |

This is the `inspector` question answered: **1, not 40.** Display panes get *touched* by everything,
which is exactly why the earlier count was worthless. The document flagged all six as
order-of-magnitude estimates; the order of magnitude was wrong.

**2. `panes` survives anyway, and on better grounds than its children.** It clears the floor at 13 — but
**5 of those are entries where a worker chose `panes` itself**, meaning the work genuinely spanned
several panes and no single child fitted. That is the grouping parent doing the job it was created for,
rather than being a bag for six thin slugs. It would clear the floor even if every child were dropped.

**3. `settings` and `workspace-bar` got zero.** Not "few" — neither worker independently placed a single
entry on either. Rule 2 admits them at generation 3 without a count, and rule 1 says they are perfectly
bounded. Neither rule says to create a slug for which no evidence exists at all. **I would not create
these two**: a slug with no precedent is a slug that will be applied wrongly the first time it is used.
`inspector` (1) and `navigation` (1) are a genuine judgement call — real but barely attested.

**4. `trace-harness` is no longer marginal.** The residual pass found five more, taking it from 7 to
**12**. The floor question that dominated the last two hours is moot on the evidence.

**5. The `memory-seed` half validated.** My hand classification agreed with the two blind workers on
**103 of 118 rows (87%)**, and the counts landed within one to three of my estimates — `topic-vocabulary`
exactly 25. The swarm found *more* `docs-lifecycle` (11 vs 8) and slightly less `lifecycle-edges`
(32 vs 35). Nothing in the split was overturned.

**6. The residual claim held.** Of the 39 `memory-seed` entries the swarm declined to file under a
child, **34 went to `OTHER-ROOT`** — their real subject is session logging, Mermaid, releases or git
housekeeping, and `memory-seed` was merely the package the work happened in. Only 5 were genuinely
`SEED-WIDE`. The residual is entries that already have a home elsewhere, which is what a healthy one
looks like.

**Reliability, for the record:** `memory-seed` agreement **119/126 = 94%** — the highest of any run so
far. The `memory-trace` residual came in at **65/79 = 82%**, the lowest. That ordering is the expected
one and worth keeping: the residual is by construction the material the earlier passes found hardest,
so a lower number there is the pool being difficult rather than the method degrading.

### The rules each row is admitted by

From [hierarchical-topic-vocabulary-proposal.md](hierarchical-topic-vocabulary-proposal.md), settled
2026-07-27:

1. **Levels must be well bounded** — a child earns its place by being distinguishable without
   judgement. The `panes` children qualify on this one strongly: each names a DOM region, so two
   siblings cannot overlap.
2. **The floor applies to generation 2 only** — `MIN_CHILD_ENTRIES = 5` decides whether a new BRANCH
   is justified. Below that there is no floor, which is why the six pane children need no count and
   `panes` itself does.
3. **A slug must fit every ancestor** — the constraint that pays for rule 2, and a worker rule rather
   than a vocabulary rule.

### The live run behind the `memory-trace` rows

Reproduce with:

```bash
python scripts/tally_swarm_area.py . --out split.json && python scripts/propose_topic_children.py score memory-trace split.json
```

Cycle 3 judged the 116 single-area entries (agreement 107/116 = **92%**); cycle 4 judged the 79-entry
residual left over (65/79 = **82%**). Together they cover the whole population.

```
parent memory-trace: 204 entries, 42.9% of 475
proposed children are generation 2 - floor of 5 applies
every claimed entry must be true at EVERY level: memory-trace > <child>

  graph                            70 entries  14.7% of corpus   ok
  panes                            13 entries   2.7% of corpus   ok
  trace-cache                      14 entries   2.9% of corpus   ok
  trace-harness                    12 entries   2.5% of corpus   ok
  trail                            34 entries   7.2% of corpus   ok

  (residual on the parent)         61 entries  12.8% of corpus

ACCEPTABLE: every child clears 5, parent falls to 12.8%
```

Both cycles quote the **agreed** column — the label both blind workers reached independently — because
a count one worker reached is a hypothesis. That is why these numbers are lower than the ones this
document carried before it was consolidated: `TRACE-WIDE` was presented as 26 and is 23.

The spread on `trace-harness` — 9 by worker 1, 7 by worker 2 in cycle 3 — was wide enough that under the
old floor of 8 it passed on one reading and failed on the other. Lowering the floor to 5 settled it
without anyone having to pick a reading, and cycle 4 then took it to 12, which settles it on evidence.

### The live run behind the `memory-seed` rows

`memory-seed` is 126 entries with **no children at all** — since the `memory-trace` split, the largest
concentration left in the vocabulary. Four children, each bounded by a path rather than a definition,
which is rule 1:

| child | the boundary that makes it unambiguous | swarm-agreed |
|---|---|---:|
| `lifecycle-edges` | `.memory-seed/sessions/links/`, the edge rules in `links check` / `link audit` | 32 here, **63** with the Seed-side `graph` entries |
| `topic-vocabulary` | `memory_seed/topics.py`, `.memory-seed/topics.yaml`, `scripts/*topic*` | 25 |
| `test-suite` | `tests/` | 12 |
| `docs-lifecycle` | `docs/` lanes, `docs check` / `docs index` | 11 |

```
parent memory-seed: 127 entries, 26.7% of 475
proposed children are generation 2 - floor of 5 applies
every claimed entry must be true at EVERY level: memory-seed > <child>

  docs-lifecycle                   11 entries   2.3% of corpus   ok
  lifecycle-edges                  32 entries   6.7% of corpus   ok
  test-suite                       12 entries   2.5% of corpus   ok
  topic-vocabulary                 25 entries   5.3% of corpus   ok

  (residual on the parent)         47 entries   9.9% of corpus

ACCEPTABLE: every child clears 5, parent falls to 9.9%
```

**`topic-vocabulary` closes a gap this work had been living inside.** The area doing the classifying had
no slug of its own, so every entry about the vocabulary — including all of today's — landed on the
`memory-seed` root with nothing more specific available.

**The residual is healthy, not homeless — and the swarm was asked to prove it.** `OTHER-ROOT` was put on
the ballot precisely so this claim could fail: it lets a worker say *the real subject is a different
existing area, and `memory-seed` is merely the package the work happened in*. Of the 39 entries declined
for a child, **34 went to `OTHER-ROOT`** and only 5 were genuinely `SEED-WIDE`. Session logging, Mermaid,
releases and git housekeeping — all already have roots. That is the opposite of the `TRACE-WIDE` problem,
where the catch-all was absorbing work with nowhere to go.

**Two candidates were declined by the floor, and correctly.** `worktree` (4 entries: the Track E
remover, the dry-run classifier, the orphaned-worktree clearance, the branch closeout) and
`constitution` (4: v1.2 ratification, v1.5, v1.6, the diagram-repair amendment). Both are real
distinctions with clean boundaries; neither has five entries yet. At a floor of 5 that is a near miss
rather than a dismissal, and either could qualify within a week.

### What is still NOT measured

Cycle 4 closed the area axis. What it did not touch:

- **`package`, `feature-build` and `testing`** — the three rows from adjudication. Keyword estimates over
  titles and bodies, the same method that put `inspector` at 40 where the swarm found 1. Treat the
  numbers as unreliable in the same way; the *categories* rest on your rulings, which is different
  evidence, not weaker.
- **Validity, as opposed to reliability.** Two workers agreeing 94% of the time means the question is
  well-posed, not that the answers are right. The held-out run put validity at **74%** against authored
  tags, and nothing since has moved that. Every count in this document is a reliable measurement of a
  judgement, not a ground truth.
- **The activity axis** has had no equivalent pass. `feature-build` at ~116 would be the largest
  activity slug in the vocabulary if the estimate is anywhere near right, and it is the one row here big
  enough that being wrong about it would matter.

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
| `memory-trace` **canonical**, today | 204 | 42.9% |
| `memory-trace` **canonical**, with the five measured children | **61** | **12.8%** |

> This row has been wrong twice, in both directions, and both times because it was a projection rather
> than a run. It first claimed **~49 / 10.6%**, assuming every candidate landed. It was then corrected to
> **85 / 18.0%** — a real scorer figure, but of a shape that excluded `panes`. The 61 above is the
> measured split with all five children, and it is what the scorer prints. The lesson is the one this
> document keeps relearning: quote the run, not the estimate.

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

This section originally rejected `inspector`, `diagram-view` and `trace-api` for want of 8 entries.
Two later rulings made most of that moot: the floor applies to **generation 2 only**, so `inspector`
and `diagram-view` are admissible as grandchildren under `panes` regardless of count, and the floor
itself came down to 5, which cleared `trace-harness`.

What survives is `trace-api` at **1 agreed** — still under a floor of 5, and with no grouping parent
to fall under. It stays on the root. That is the rule doing its job rather than failing: a single
entry is not a category, at any floor.

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

| slug | the region it names | keyword est. | **measured** | |
|---|---|---:|---:|---|
| `graph` | `GraphWorkspace` — the relationship map | 146 | **70** | not a pane; a workspace, reparented from root |
| `trail` | `TrailWorkspace` — the timeline | 133 | **34** | not a pane; a workspace |
| `panes` | the grouping parent for the six below | ~23 | **13** | 5 of those chose `panes` itself |
| `inspector` | `<aside class="inspector">` — the reader | ~40 | **1** | |
| `topbar` | `<header class="topbar">` — search, view switch, worktree picker, refresh | ~17 | **4** | |
| `navigation` | `<aside class="navigation-pane">` — project, topics, context list | ~14 | **1** | replaces the earlier `context`, which was a SECTION inside it |
| `settings` | `SettingsMenu.tsx` | ~14 | **0** | |
| `workspace-bar` | scope / range / labels / edge filters | ~11 | **0** | |
| `diagram-view` | `DiagramViewer.tsx` | 4 | **2** | |
| `trace-cache` | startup, caching, freshness, worktree switching | 12 | **14** | not a pane |
| `trace-harness` | Storybook, Playwright, e2e, CI wiring | 7 | **12** | not a pane |

**The keyword column was wrong by up to 40x, and the reason is worth keeping.** It counted keyword
presence over titles and bodies, which measures *which pane a change mentioned* — and a display pane
gets mentioned by nearly everything. The swarm was asked what the entry is ABOUT. `inspector` is the
extreme case: ~40 by keyword, **1** by two workers judging independently.

The keyword numbers were never useless — they established that each pane is *nameable*, which is rule 1
and is why `panes` survives. They were just never a count of anything.

**What naming every pane did to `TRACE-WIDE`:** re-ruling the 22 adjudicated rows with the full set
moved three of six off it, all to `topbar` (search routing, full-text navigation, the unified find bar).
`TRACE-WIDE` now holds three: a package-wide module rename, a multi-pane design pass, and a loading
mechanism JNL ruled wide-impact. That is what the answer should mean — cross-cutting, not homeless.

### AREA — elsewhere

| slug | entries | evidence |
|---|---|---|
| `lifecycle-edges` under `memory-seed` | **63** measured | takes `graph`'s four current children, which are all edge-MODEL concepts |
| `package` (root) | ~66, unmeasured | JNL, from adjudicating row 3; spans Seed and Trace, currently homeless |

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
- **The `memory-seed` classification is committed** as
  `docs/4_Reference/memory-seed-area-split.tsv` — all 126 entries with their assigned child (or
  `RESIDUAL`) and title, so the split can be argued with line by line instead of taken on trust. Feed
  it to the scorer by pivoting it into `{child: [ids]}`.
- **Cycle 4's raw answers are committed** as
  `docs/4_Reference/topic-swarm-cycles/cycle4-{trace-residual,seed-population}-w{1,2}.tsv`, one file per
  worker per population. `scripts/tally_area_swarm_json.py` rebuilds the agreement table, the
  disagreement list and the scorer split from a run's JSON.
- Re-run everything with:
  `python scripts/measure_topic_concentration.py`
  `python scripts/tally_swarm_area.py . --out split.json`        (cycle 3)
  `python scripts/tally_area_swarm_json.py answers.json mt`       (cycle 4)
  `python scripts/propose_topic_children.py score memory-trace split.json`
  `python scripts/propose_topic_children.py gather memory-seed`
- The scorer's floor and target are stated in code (`MIN_CHILD_ENTRIES`, `TARGET_PARENT_SHARE`), and it
  scores the *canonical* residual, not reach.
