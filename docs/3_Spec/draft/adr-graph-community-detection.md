---
title: ADR graph community detection
status: draft
spec_binding: draft
parent: ../../2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md
---

# ADR: Community Detection On The Trace Graph

Status: **DRAFT - RECOMMENDS NOT IMPLEMENTING**. This ADR exists to close the question, record what
was measured, and stop it being reopened from first principles.

Investigated 2026-07-22 against the live corpus: 565 entries, 669 authored edges, 359 entries (64%)
carrying at least one topic. Measurement scripts are throwaway (`uv run --no-project --with networkx
--with scikit-learn`); no dependency was added to any manifest.

## Question

Proposal §4.3 assumes communities come from Leiden/Louvain and specifies a fingerprint /
member-overlap / `community_previous_id` apparatus to stabilise their unstable ids. Entry
`mse_xmtax6v2sn6hybzk` recorded the work as blocked rather than guess a design. Entry
`mse_3yvakpxdshc95e68` then shipped communities derived from **authored topics** instead, which made
that apparatus unnecessary rather than pending.

This ADR asks the remaining question: does structural detection recover anything the authored topics
do not, and specifically, would it license colouring the 36% of entries that carry no topic?

## Method, and why it is not modularity

Modularity alone cannot answer this. A partition can score extremely well on modularity while
bearing no relation to what the graph is *about* - and that is exactly what happened here: the
authored-edge graph yields **modularity 0.89 with ARI 0.11 on the same partition**. Optimising
modularity would have declared success.

So topics are used as **ground truth, never as input**. Every clustered edge set below excludes topic
chains and topic cliques. Agreement is measured with Adjusted Rand Index and Normalised Mutual
Information against the 15 authored communities, on the 355 labelled nodes only. High agreement
would license trusting detected labels on the unlabelled remainder. Low agreement withholds it.

Ground truth is the *shipped* rule, not raw topics: a node's community is its most distinctive topic
(lowest corpus frequency) among those clearing a corpus-frequency floor of 10.

### Baselines and controls

| Control | ARI | NMI | Reading |
|---|---|---|---|
| Random partition, k=15 | −0.0034 | 0.114 | The floor. |
| **Topic cliques as input, no size ceiling** | **+0.2720** | 0.519 | **The ceiling.** |

The second row is the single most important number in this document and it is not the one that was
expected. Feeding the ground truth **in** as edges still only scores 0.272. The reason is structural:
the truth is not a graph partition at all. It is a per-node label distilled from *overlapping* topic
memberships - 308 of 565 entries carry two or more topics - so no partition of the graph can
reproduce it exactly, and Louvain fragments even a clique graph into k=214.

**Every detection score below must be read against a maximum of ~0.27, not 1.0.**

> A first version of this control capped topic cliques at 25 members, the same ceiling used for file
> groups. That excluded all five topics large enough to define a community (169, 84, 66, 66, 57
> members), so it measured whether *small* topics are recoverable and nothing else. It reported
> 0.184 and was invalid. Recorded here because the corrected control changed the interpretation of
> the whole investigation, not the verdict.

## Phase 1: is anything dense enough to partition?

Expected to kill or redirect the work before clustering ran. It redirected it.

Group expansions are capped at 25 members. The largest file groups are `CHANGELOG.md` (161),
`tests/test_memory_seed.py` (104), `memory_seed/core.py` (100), `docs/2_Todo/0_NEXT_STEPS.md` (89),
`.memory-seed/agent-rules.md` (77) - hub files nearly every change touches, carrying no more
discriminative signal than a stopword. Uncapped, file cliques alone would contribute 93,241 edges
and swamp all 669 authored ones.

| Edge set | E | deg/node | isolated | density | components | giant |
|---|---:|---:|---:|---:|---:|---:|
| A authored only | 633 | 2.24 | 107 | 0.0040 | 10 | 75.4% |
| AF authored+files | 6,017 | 21.30 | 12 | 0.0378 | 5 | 92.9% |
| AB authored+branch | 974 | 3.45 | 99 | 0.0061 | 9 | 78.1% |
| AFB authored+files+branch | 6,287 | 22.25 | 10 | 0.0395 | 5 | 93.3% |

**Authored-only is too sparse to partition reliably** - 2.24 edges per node with 107 nodes at zero.
That was the predicted outcome and it held. **Files are the lever that rescues density**, taking
degree from 2.24 to 21.3 and isolated nodes from 107 to 12. Branch membership adds almost nothing
(+341 edges) because 148 of the 174 distinct branches hold a single entry.

So the question became the intended fallback: *which derived edges must be admitted to reach usable
density?* Answer: files, and only files.

## Phase 2: agreement

Axes swept: edge set (A / AF / AB / AFB) × weighting (uniform vs `EDGE_PRIORITY`, supersedes 8 /
evolves 4 / related 1) × resolution × 3 seeds — 144 configurations in the main sweep, plus a
low-resolution matched-k sweep and an 11-point best-effort sweep reported below.

Best agreement found anywhere in the sweep:

| Edge set | Best ARI | NMI | at resolution | k |
|---|---:|---:|---:|---:|
| A authored | +0.1205 | 0.469 | 2.0 | 145 |
| AF authored+files | +0.1142 | 0.367 | 2.0 | 43 |
| AFB authored+files+branch | +0.1079 | 0.399 | 3.0 | 49 |

Weighting by `EDGE_PRIORITY` helps marginally and consistently (A: 0.0920 → 0.1059 at resolution
1.0), confirming that unweighted clustering is mostly clustering on `related` - 533 of 669 authored
edges. It does not change the verdict.

### The measurement that decides it

ARI is depressed by granularity mismatch, so detection was also judged at **matched k**, pushing
resolution down until the community count approaches the truth's 15. This is the fair comparison and
it is where detection fails outright:

| Edge set | resolution | k | ARI | largest community |
|---|---:|---:|---:|---:|
| AF authored+files | 0.02 | 17 | +0.0001 | **92.9%** |
| AF authored+files | 0.05 | 18 | +0.0001 | 89.0% |
| AFB authored+files+branch | 0.02 | 15 | **−0.0006** | **93.3%** |
| AFB authored+files+branch | 0.05 | 16 | −0.0006 | 88.8% |

At exactly the granularity a 16-colour legend needs, detection produces **one blob holding 93% of
the graph plus dust, and agreement indistinguishable from zero** - a worse partition than the
connected-components attempt (454/4/4/3/2) that was rejected earlier. The 0.11 scores are only
reachable at k=43–145, which is unusable for colouring and is itself only 44% of the 0.272 ceiling.

## Rejected variants, with the numbers

| Variant | Result | Why rejected |
|---|---|---|
| **Authored edges only** | deg 2.24/node, 107 isolated, density 0.004 | Too sparse to partition reliably. Predicted, confirmed. |
| **Branch as membership** | +341 edges; best ARI 0.101 vs 0.093 for authored alone | 148 of 174 branches hold one entry. Adds cost, not signal. |
| **Uniform weighting** | ARI 0.0920 vs 0.1059 weighted | With 533 related vs 6 supersedes, uniform clusters on `related` alone. |
| **Matched-k detection (k≈15)** | ARI ≈ 0.000, largest 93% | The decisive failure. Unusable at legend granularity. |
| **Time as weight decay** | ARI 0.075–0.108 across half-lives 7/14/30/90d, flat | No effect at any half-life. Tested because it was specified; null result. |
| **Raising the file ceiling** | ARI 0.089→0.101 from ceiling 10→80; Q(truth) *falls* 0.242→0.149 | Admitting hub files adds edges and destroys topic alignment. |
| **Modularity as the score** | Q=0.89 with ARI=0.11 | Would have declared the worst-agreeing configuration a success. |

## What the graph *does* say

The negative verdict is not "the graph has no structure". It has plenty - detected modularity 0.72–0.89.
The structure is simply **not the topic structure**; detection recovers file-locality and
work-session clusters, a different and legitimate partition that is not the one the legend names.

Two constructive findings are worth keeping:

**Authored lifecycle edges are strongly topic-aligned.** Against an 8.1% chance rate:

| Edge type | Intra-community | Rate | vs chance |
|---|---|---:|---:|
| `supersedes` | 4/4 | 100.0% | 12.3× |
| `evolves` | 76/123 | 61.8% | 7.6× |
| `related` | 134/327 | 41.0% | 5.1× |

The signal is real and strong; there is simply not enough of it - 4 supersedes pairs among labelled
nodes. This supports the *existing* one-hop faded inference for topicless entries, which uses
precisely these edges, and suggests that authoring more lifecycle edges would improve the graph more
than any algorithm.

**The authored partition is genuinely cohesive** on authored edges: modularity of the truth partition
is 0.370, with 45.1% of authored edges falling inside a community against 8.1% by chance. Topics are
not arbitrary labels over the graph. They are just not recoverable *from* it at usable granularity.

## Stability, if it had been adopted

Recorded because it sizes the §4.3 apparatus a shipped version would have needed:

| Edge set | Seed stability (mean pairwise ARI) | Growth stability (50%→full) | (80%→full) |
|---|---:|---:|---:|
| A authored | 0.929 | 0.780 | 0.891 |
| AF authored+files | 0.739 | 0.926 | 0.759 |
| AFB | 0.797 | 0.926 | 0.790 |

Between 7% and 26% of nodes change community across corpus growth, and up to 26% across a seed
change alone. A shipped detection scheme would therefore need the full fingerprint / member-overlap
/ `community_previous_id` retention apparatus, plus a pinned seed, before a single colour could be
trusted between two page loads. Authored-topic communities need none of it: measured 0 changes
across growth and rebuild, because a topic slug is a stable identity by construction.

## Recommendation

**Do not implement community detection.** Keep authored-topic communities as shipped
(`mse_3yvakpxdshc95e68`). Keep the one-hop faded neighbour inference for topicless entries
(`mse_ftx8e1d5hwysajsz`) as the mechanism for the 36%.

The reframe that motivated this investigation - high agreement would license trusting detected
labels on the topicless remainder - resolves cleanly in the negative. Agreement is 0.11 against a
0.27 ceiling, and at the granularity that would be needed, **73% of the 210 topicless nodes land in
a single community** (k=18). A detected label would carry almost no information for exactly the
nodes it was wanted for.

Consequently §4.3's stable-community apparatus should be marked **not required** rather than
outstanding, and the topology proposal's assumption that communities come from Leiden/Louvain should
be amended to record that this was measured and rejected.

## Limitations, recorded not hidden

- **Louvain, not Leiden.** networkx ships Louvain; Leiden needs `leidenalg`/`igraph`, which the
  no-new-dependency constraint excluded. Leiden guarantees well-connected communities and typically
  improves partition quality. It shares the resolution-limit behaviour that produces the 93% blob at
  low k, so it is judged unlikely to overturn the matched-k result — but it is **untested**, and that
  is the single most credible route to challenging this ADR.
- **Direction is lost.** Both algorithms are undirected, so `supersedes`/`evolves` lineage direction
  is discarded. A directed method might read lineage chains differently. Given there are 6 supersedes
  edges in the whole corpus, this is unlikely to matter yet.
- **Files and branch are derived-but-not-artefactual**, a different category from the topic and day
  chains demoted on 2026-07-22. A file edge reflects two entries genuinely touching the same code; it
  is weaker evidence than an authored link, not fabricated evidence.
- **One corpus, one author.** Every number here is from a 565-entry corpus written by one person. A
  larger or multi-author corpus could have denser authored linking and a different answer.
- Group cliques are normalised by `1/(size−1)`, so a large group does not outweigh authored edges by
  sheer count. An unnormalised variant was not swept.
