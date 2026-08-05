---
title: "Relevance Band Calibration Findings"
date: "2026-08-05"
project: "memory-seed"
status: "measured; recommendation pending decision"
priority: "P1"
next_action: "Decide between replacing the floor with top_over_median and deleting the band; recall is the larger finding and needs its own work item."
related:
  - "docs/2_Todo/attention-retrieval-signal-proposal.md"
  - "experiments/decision-retrieval-scale/measure.py"
  - "docs/CONSTITUTION.md"
---

# Relevance band calibration - findings

> **Correction, 2026-08-05 (later the same day). Read this before any number below.**
>
> This run's harness did not mirror the production read path, in two ways, so some figures are void.
> Both were caught after publication - the first by JNL doubting a number that looked too small.
>
> **(a) The corpus was read raw.** `extract_memory_chunks` carries no sidecar edges, and lifecycle
> edges are authored into link sidecars *after* an entry is written. Read through `load_corpus`
> (added 2026-08-05), the corpus holds **23 `replaced_by` and 290 `evolved_by`**, not the 4 and 136
> reported below. The statement "the corpus contains only 4 `replaced_by` edges across 808 nodes" is
> **wrong**, and every lifecycle figure derived from it is withdrawn.
>
> **(b) The ranker was called bare.** `rank_session_memory` defaults `supersession_damping` and
> `replacing_successor_boost` to False; `search_memory` sets both True. The harness took the
> defaults, so it measured a configuration nobody runs.
>
> **What survives**, because it depends on neither defect: score invariance across corpus size (§1),
> the best spurious match rising with N (§1), the shipped rule's specificity of 0.00 over 34
> negatives (§2 - negatives carry no lifecycle edges), cost being flat in corpus size (§4), and the
> semantic component's 21.6% share with the weight sweep's 62% → 78% (§4b).
>
> **What is withdrawn pending re-measurement:** all of §5's lifecycle rows and the `P_life` sample of
> 4; and §4c's 8.3-point recency figure, measured with supersession damping off. Re-baselined
> lifecycle numbers are in `lifecycle-guard-baseline.json` - replaces n=23, replacement surfaces
> 20/23 and outranks the retired entry 22/23; evolves n=97, newer form surfaces 36/97.
>
> The stored `results-*.json` were deleted rather than kept: a saved result produced by a broken
> instrument invites exactly the mistake that produced it. The scripts regenerate them.

Corpus: 842 entries / 1,252 decision chunks. 278 labelled queries (244 positives from three
mechanical sources, 34 negatives). Fit/held-out split stratified by source. Kill condition stated
before the run: *if no statistic reaches 0.80 held-out balanced accuracy with a CI excluding 0.5,
delete the band rather than ship a retuned version of the same false confidence.*

## 1. The premise of the proposal was wrong, and the conclusion survives anyway

The plan assumed the constants failed because scores drift with corpus size (IDF). Reading
`_lexical_score` contradicted that - it is pure per-chunk term overlap with fixed field weights
(tags 12, contexts 8, heading_path 6, lexical_terms 4, +1 per term in body text), with no corpus
statistics anywhere. The N-curve was then run as a test of that reading rather than as a fit.

Holding each query and its correct answer fixed and varying only the number of distractors:

| N entries | positive's own score | top of result set | positive/top | negative's top |
|---|---|---|---|---|
| 25 | 17.962 | 20.81 | 0.878 | 19.13 |
| 50 | 17.962 | 21.41 | 0.861 | 22.32 |
| 100 | 17.962 | 23.80 | 0.793 | 23.48 |
| 200 | 17.962 | 23.69 | 0.761 | 25.56 |
| 400 | 17.962 | 27.57 | 0.713 | 26.10 |
| 800 | 17.962 | 29.19 | 0.672 | 27.79 |

A positive's absolute score is **exactly invariant** to corpus size - 17.962 at every N, not
approximately. The reading was right and the proposal's premise was wrong.

**But the floor breaks with scale anyway, by a different mechanism.** The best *spurious* match
improves as the corpus grows: a negative's top score climbs 19.1 → 27.8. By 800 entries the average
negative's best result (27.8) **outscores the average positive's own answer** (17.96). No absolute
floor can sit between them, and the gap widens with growth. The absolute floor is not mistuned; it
is the wrong kind of statistic, and it gets worse every time the store grows.

The `0.55 of top` ratio degrades too, from the other direction: a true answer sits at 0.878 of the
top score at N=25 and 0.672 at N=800. Extrapolating, real answers start falling below the 0.55
strong/weak boundary somewhere in the low thousands of entries.

## 2. The shipped rule is not uncalibrated - it is inverted

On all 34 negatives, floor 6.0 flags "there is an answer here":

- sensitivity **1.00**, specificity **0.00**, balanced accuracy **0.50** - exactly chance
- 34 of 34 negatives called answerable; specificity 95% CI **[0.00, 0.10]**

This replicates the morning's 12-query finding on 34 negatives including 24 fluent,
plausible-sounding software questions. The rule says yes to everything, so it carries no
information. The morning's mitigation (label the payload `relevance_calibrated: False` and tell
agents to judge from content) was the right call and remains necessary.

## 3. A scale-free statistic does work

Thresholds fitted on half the labels, reported on the held-out half (122 positives, 17 negatives):

| statistic | threshold | sens | spec | balanced acc | held-out AUC (95% CI) |
|---|---|---|---|---|---|
| `top_over_median` | 1.317 | 0.74 | **1.00** | **0.87** | **0.899 [0.840, 0.945]** |
| `matched_frac` | 0.578 | 0.69 | **1.00** | 0.84 | 0.850 [0.783, 0.914] |
| `gap1` | 1.129 | 0.61 | 0.71 | 0.66 | 0.798 [0.702, 0.883] |
| `top_per_term` | 5.388 | 0.42 | 1.00 | 0.71 | 0.689 [0.587, 0.784] |
| `robust_z` | 6.818 | 0.58 | 0.65 | 0.61 | 0.699 [0.574, 0.806] |
| `top_abs` (shipped) | 36.145 | 0.53 | 0.76 | 0.65 | 0.658 [0.549, 0.758] |

`top_over_median` clears the pre-registered kill condition: 0.87 held-out balanced accuracy, AUC CI
well clear of 0.5, and it rejected **every** held-out negative. Note that even re-fitted optimally,
the shipped statistic `top_abs` only reaches 0.65 - the problem was never the value of the constant.

Stability across corpus size (AUC, positives stratified across all three label sources):

| N | `top_abs` | `matched_frac` | `top_over_median` |
|---|---|---|---|
| 25 | 0.753 | **0.894** | 0.858 |
| 50 | 0.707 | **0.900** | 0.814 |
| 100 | 0.729 | 0.861 | **0.900** |
| 200 | 0.708 | 0.820 | **0.849** |
| 400 | 0.731 | 0.836 | **0.890** |
| 800 | 0.720 | 0.837 | **0.876** |

`top_over_median` is flat-to-rising with corpus size; `matched_frac` is strongest on a small store
and decays. That is the small-vs-large answer, and it is a genuine crossover rather than one
statistic dominating: a blend, or a size-dependent choice, is defensible. Neither needs a constant
that depends on N.

## 4. Cost does not scale with corpus size

Served payload, top-8, with `DECISION_TEXT_LIMIT` applied:

| N | 25 | 50 | 100 | 200 | 400 | 800 |
|---|---|---|---|---|---|---|
| ~tokens | 3691 | 3662 | 3430 | 3707 | 3493 | 3595 |

Flat. Cost is a function of `top_k` × chunk size, not of how much is stored, so there is no
large-corpus cost problem to solve - the levers are `top_k` and `DECISION_TEXT_LIMIT`. Worth noting
the measured mean (~3.6k tokens) runs above the ~2.3k "typical" figure recorded when decision
granularity shipped.

## 4b. The semantic arm changes almost nothing - and that is the finding

Everything above replicates with the shipped default (semantic ranking on, local Model2Vec
`potion-base-8M`, no API cost):

| | lexical | semantic |
|---|---|---|
| positive's score across N | 17.962 (invariant) | 18.909 (invariant) |
| negative's top score, N=25 → 800 | 19.1 → 27.8 | 19.7 → 28.3 |
| shipped rule specificity | 0.00 (34/34) | 0.00 (34/34) |
| `top_over_median` held-out AUC | 0.899 [0.840, 0.945] | 0.900 [0.842, 0.946] |
| `top_abs` held-out AUC | 0.658 | 0.662 |
| paraphrase answer in top 8 | 63/120 | 63/120 |

Turning semantic ranking on moves paraphrase recall by **zero**. The cause is the blend:

```
semantic_component = max(cosine, 0.0) * 3.0      # semantic_cache.py:927
match_score        = lexical_score + semantic_component
```

Cosine is bounded by 1, so a *perfect* semantic match is worth 3.0 - less than one heading-path
term match (6.0) and a quarter of one tag match (12.0). Measured, the semantic component is 21.6%
of `match_score` on average and cannot reorder anything separated by more than three lexical
points. Semantic ranking is nominally enabled and effectively decorative.

**It is not that the embedding carries no signal.** Sweeping the weight, holding everything else
fixed (120 paraphrase queries, corpus embedded once):

| weight | 0 | 3 (shipped) | 10 | 30 | 60 | 120 |
|---|---|---|---|---|---|---|
| answer at rank 1 | 36 | 38 | 39 | 45 | **54** | 55 |
| answer in top 8 | 73 | 74 | 79 | 85 | **94** | 93 |

At weight 60 the right entry reaches the top 8 in 78% of paraphrase queries instead of 62%, and
rank 1 goes from 38 to 54 of 120. The curve turns over by 120, so the optimum is a real interior
point rather than "more is better". The embedding was carrying usable signal the whole time; the
blend was throwing it away.

*(Sweep numbers are not directly comparable to the table above - the sweep applies no recency
multiplier and dedupes to eight distinct entries. Within the sweep the method is constant, so the
trend across weights is what it measures.)*

## 4c. Recency weighting costs recall in a decision store

Chasing the discrepancy between the sweep's 73/120 baseline and the harness's 63/120 isolated a
second cause - not deduplication (a top-8 chunk window covers 7.47 distinct entries on average, so
crowding is negligible) but the recency multiplier:

| | answer at rank 1 | answer in top 8 |
|---|---|---|
| recency on (shipped) | 34/120 | 63/120 |
| recency off | 37/120 | **73/120** |

Recency weighting removes 10 of 120 correct answers from the top 8 - 8.3 percentage points. In a
store whose purpose is retrieving *old decisions*, down-weighting age is at least worth an explicit
argument; at present `lambda_days=0.01` was never validated against recall.

## 5. The larger finding: recall, not the band

Answer-rank health on the positives (lexical arm):

| source | n | answer at rank 1 | answer in top 8 |
|---|---|---|---|
| `P_title` (query = entry title) | 120 | 117 (98%, CI 93-99%) | 120 |
| `P_terms` (query = words from the decision) | 120 | 34 (28%, CI 21-37%) | 63 (53%) |
| `P_life` (retired title → live head) | 4 | 0 | 2 |

Ranking works when the query matches the title. When the query is a *paraphrase* - content words
drawn from the decision body, which is what "agent half-remembers a decision and asks about it"
actually looks like - **the correct entry never appears in the top 8 at all, 47% of the time.**

No band can fix that. A perfect abstention signal on top of 53% recall correctly tells the agent
"nothing found" while the answer sits in the store. This is a bigger problem than the one we set
out to solve, and it deserves its own work item.

`P_life` is n=4 because the corpus contains only **4** `replaced_by` edges across 808 nodes (there
are 144 `evolves`). Any lifecycle-stability claim in this project - including the one in
`decision-retrieval-scale/measure.py`, which requested 25 and could only have received 4 - rests on
that sample. It should be re-derived from `evolves` edges to have any power.

## Caveats

- **Both arms were measured.** Tables in sections 1-3 and 5 are the lexical arm; section 4b gives
  the semantic comparison, which differs negligibly for the reason set out there.
- **The negatives are easier than they look.** Under a lexical ranker, "the corpus lacks these
  words" is close to "scores low". A statistic that fails on these is decisively broken; one that
  passes has cleared a low bar. The semantic arm does not fix this, because the semantic component
  is too small to move the ordering.
- **The weight sweep optimum (60) is fitted on all 120 paraphrase queries**, with no held-out split,
  so it is a direction and an order of magnitude - not a constant to ship. Any actual change to the
  blend needs its own held-out fit, and `ranking-ab` cannot gate it (the gate covers boolean signal
  flips, not weight changes).
- **`P_terms` and `P_title` draw the query from the target entry**, so they are partially circular.
  `P_title` is a sanity floor only. `P_life` is the least circular and has almost no data.
- 17 held-out negatives is a small denominator. AUC with a bootstrap CI is reported instead of a
  pass/fail verdict for that reason.

## Recommendation

**The band was the wrong thing to worry about.** It is broken - specificity 0.00 - but it is a
label on top of retrieval, and the measurements say retrieval itself is losing roughly a third of
its achievable recall to two constants nobody validated.

In priority order:

1. **Raise the semantic blend weight.** The single largest measured win: paraphrase recall in the
   top 8 goes from 62% to 78%. Needs its own held-out fit before a number is chosen; 60 is a
   direction, not a value to ship.
2. **Re-examine the recency multiplier.** Worth 8.3 points of recall, and the argument for
   down-weighting age in a decision archive has never been written down.
3. **Replace the absolute floor with `top_over_median`** (threshold ≈1.22-1.32, held-out balanced
   accuracy 0.85-0.87 across both arms). Do *not* retune 6.0 - the N-curve shows no value of it can
   work, and re-fitting it optimally still only reaches 0.65. Consider blending in `matched_frac`,
   which is the stronger statistic below ~100 entries.
4. **Keep `relevance_calibrated: False`** until 1 and 2 land, because both change the score
   distribution the threshold would be fitted against. Fitting the band first would mean fitting it
   twice.
5. **Re-derive the lifecycle labels from `evolves`.** Four `replaced_by` edges cannot support any
   claim, including the ones already recorded.
