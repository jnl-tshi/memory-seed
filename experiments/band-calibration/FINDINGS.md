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

- **All numbers above are the lexical arm.** The shipped default has semantic ranking on via a local
  Model2Vec provider (`potion-base-8M`, no API cost). The semantic arm is measured separately; the
  recall figure in particular is the one most likely to move.
- **The negatives are easier than they look.** Under a lexical ranker, "the corpus lacks these
  words" is close to "scores low". A statistic that fails on these is decisively broken; one that
  passes has cleared a low bar.
- **`P_terms` and `P_title` draw the query from the target entry**, so they are partially circular.
  `P_title` is a sanity floor only. `P_life` is the least circular and has almost no data.
- 17 held-out negatives is a small denominator. AUC with a bootstrap CI is reported instead of a
  pass/fail verdict for that reason.

## Recommendation

Replace the absolute floor with `top_over_median`, keep `relevance_calibrated: False` until the
semantic arm confirms the threshold transfers, and open recall as a separate work item. Do **not**
retune 6.0 - the N-curve shows that number cannot be made to work at any value, and re-fitting it
optimally still only reaches 0.65.
