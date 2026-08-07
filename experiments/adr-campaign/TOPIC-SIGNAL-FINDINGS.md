# Exploratory analysis: what are topics actually good for? — 2026-08-07

Run on JNL's instruction to treat this as EDA: audit the data and the join logic first, then TEST
the candidate approaches before implementing any of them. Two of the four tested ideas were
abandoned as a result, including one I had recommended.

> **Rewritten twice.** The first version reported that 77% of lineage edges had an untopiced end
> and concluded "coverage is the binding constraint". That was a join bug: most edge *targets* are
> stored as bare entry ids, and the script keyed them against an `entry:ordinal` topic map, so every
> bare-target edge silently missed. JNL challenged it ("I thought the topic sidecar had already
> provided topics for all decisions"), and was right. The join now lives in
> `audit_link_topic_join.py` so no analysis re-derives it.

## Step 0 — data audit (`audit_link_topic_join.py`)

| check | result |
|---|---|
| edge kinds | 232 `evolves`, 8 `replaces`, 75 `related` |
| ref forms | **no edge has both ends bare**; 244 of 315 have one bare end — normalisation is mandatory |
| usable lineage edges | 231 (9 dropped: bare ref whose entry has several decisions) |
| **direction** | **231 of 231 point backward in time** — the forward-only invariant holds empirically |
| hygiene | 0 intra-entry edges, 0 duplicate triples |
| provenance | 27 authored, 204 machine-scored |
| topics on both ends | 225 of 231 (**97%**) |
| topics per decision | 1006 have exactly 2 (area+activity), 47 have 1 |

**Topic coverage decays after the swarm.** By entry month: May 100%, June 100%, July 92%,
**August 6%**. The swarm ran 2026-07-27/28 and was a snapshot; nothing keeps up with new decisions.
This is the concrete argument for S2's write-time attribution — the corpus is already drifting out
of coverage a week later.

*(34 attributions carry an empty ordinal — entry-level topics in a decision-keyed field. Benign;
treat as applying to the entry's decisions.)*

## Test 1 — can topics RANK attachment candidates? **No.**

Ground truth: JNL's 5 approved picks from the screening shortlist. Each ADR offered 5 candidates,
so random selection scores mean rank 3.0.

| scorer | approved ranked #1 | mean rank |
|---|---|---|
| shared-topic count (what we ship today) | 0/5 | **3.00 — exactly random** |
| IDF (rarity weighting) | 0/5 | 2.80 |
| semantic similarity | 1/5 | 2.20 |
| IDF + semantic | 0/5 | 2.80 |

**Do not build the rarity/semantic ranker.** I recommended it in the previous version of this
document; it does not survive contact with the labelled set. The gains are inside noise at n=5, and
the current scorer is indistinguishable from chance.

**But recall is excellent: 5 of 5 approved picks were present in the offered candidate list.** So
topics do the surfacing job well and the selection job not at all. What actually selected correctly
was a worker *reading the decision body*. Keep topics for bounding the candidate set; keep reading
for choosing within it.

## Test 2 — can topics SEGMENT lineage into concern chains? **Yes, clearly.**

| rule | edges kept | components | largest |
|---|---|---|---|
| no filter | 231 | 50 | **58** |
| shared ancestor | 164 (71%) | 59 | 28 |
| leaf slug | 136 (59%) | 58 | 18 |
| **same area** | **85 (37%)** | 42 | **11** |

Coherence by inspection — the point of the test:

- **Unfiltered largest (58 nodes)** spans `session-logging`, `docs-lifecycle`, `panes`,
  `lifecycle-edges`, `graph`, `package`, `trail`. Not a concern; a hairball.
- **Same-area largest (11 nodes)** is entirely `mcp-tools`: *"Codex MCP belongs in project
  .codex/config.toml"*, *"Write MCP config unconditionally, no PATH check at init"*, *"Claude MCP
  server belongs in project-root .mcp.json"*, *"MCP upsert: overwrite if command matches"*. That is
  one concern, and it reads like an ADR that does not exist yet.
- Next chains are equally clean: `session-fuse` (8), `docs-lifecycle` (6), `trail` (6).

**This is the thing to build.** It also has a second use nobody asked for: a coherent chain with no
ADR attached to it is a *candidate concern* — which is a better ADR-discovery mechanism than the
control-file harvest that seeded the corpus.

## Test 3 — hop types

Activity transitions: `feature-build → feature-build` (14), `feature-build → bugfix` (6),
`bugfix → feature-build` (3), `design-evaluation → feature-build` (3). A recognisable development
lifecycle — and the reason a same-activity requirement fails: the commonest hop keeps the activity,
the next commonest change it. Cross-area transitions are all singletons or pairs: no usable prior.

## Test 4 — semantic similarity as a gate

Aggregate signal is real: observed hop topic-pairs mean cosine **0.107** vs random **0.062**
(n=714, lift ~1.7×). It captures adjacency exact matching misses —
`cos(session-logging, session-fuse) = 0.417`, a known-good hop leaf matching blocks.

But on the labelled hops it does not separate. Max-pooled, the **bad hop scores highest of all**
(0.403) via `feature-build ↔ skill-architecture` — an activity compared against an area.
Axis-matching removes that nonsense but leaves the bad hop (0.086) *between* good hops at 0.065 and
0.417. No threshold works. **Authorship remains the gate** (27 authored edges; it separates all
labelled cases correctly).

## Where this lands

| job | use | evidence |
|---|---|---|
| **grouping** lineage into concern chains | **same-area filter** | coherent chains, 58 → 11 |
| **recall** — bounding a candidate set | topic match | 5/5 golds surfaced |
| **ranking** within a candidate set | ~~topics~~ → **read the decision** | all scorers ≈ random |
| **gating** a head move | **authorship** | topics fail at every granularity |

Two of these were things I proposed and the data rejected. Worth stating plainly: the exploratory
pass paid for itself twice.

**Caveat: n=5 labelled picks and n=5 labelled hops.** Every claim about ranking and gating rests on
that. Test 2's coherence result is qualitative but rests on all 231 edges, and is the most robust
finding here.
