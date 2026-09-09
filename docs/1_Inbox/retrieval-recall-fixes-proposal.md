---
title: "Retrieval Recall Fixes Proposal"
date: "2026-08-05"
project: "memory-seed"
status: "proposed; none applied"
priority: "P1"
next_action: "Re-derive lifecycle labels from evolves edges (F0) - F2 cannot detect its own regression without them."
related:
  - "experiments/band-calibration/FINDINGS.md"
  - "docs/1_Inbox/ranking-ab-unit-change-gate-proposal.md"
  - "docs/CONSTITUTION.md"
---

# Retrieval recall fixes

Four fixes and one prerequisite, from `experiments/band-calibration/FINDINGS.md`. None is applied.
Ordered by dependency, not by size.

Common validation rules for all of them:

- **Held-out.** Thresholds and weights are fitted on half the labels and reported on the other half.
  A number fitted on the set it is reported against is not evidence.
- **`ranking-ab` cannot gate any of these.** It covers boolean signal flips over a fixed corpus, not
  weight changes - the same structural limit recorded in
  `ranking-ab-unit-change-gate-proposal.md`. The gate here is the held-out measurement plus the
  named non-regression guards below, recorded as a decision.
- **Every guard is a test that can fail.** State what would make you distrust the result and confirm
  it is absent (`risk_signaling.md`).

---

## F0 (prerequisite) - Re-derive lifecycle labels from `evolves`

**Problem.** The corpus holds **4** `replaced_by` edges across 808 nodes, against **144** `evolves`.
Every lifecycle claim in this project rests on n=4, including
`decision-retrieval-scale/measure.py`, which requested 25 targets and could only ever have received
4.

**Change.** Extend `experiments/band-calibration/labels.py::lifecycle_positives` to build targets
from `evolves` edges as well as `replaced_by`, tagged by edge type so the two are never pooled
silently.

**Why it comes first.** F2 removes or weakens recency. Recency exists to prefer *current* decisions
over retired ones. Without a lifecycle label set with real power, F2 cannot detect the regression it
is most likely to cause - it would look like a clean win while quietly surfacing stale decisions.

**Guard.** Report `replaced_by` and `evolves` results separately. If they disagree, that is a
finding, not noise to average away.

---

## F1 - The lexical/semantic blend

**Problem.** `semantic_cache.py:927`:

```python
semantic_component = max(semantic_score or 0.0, 0.0) * 3.0
match_score        = lexical_score + semantic_component
```

Cosine is bounded by 1, so a perfect semantic match contributes 3.0 against one tag match's 12.0.
Measured semantic share of `match_score`: **21.6%**. Turning semantic ranking on changes paraphrase
top-8 recall by exactly zero (63/120 both ways).

**The naive fix is not the right fix.** Raising the constant to ~60 lifts top-8 paraphrase recall
from 62% to 78%, which proves the embedding carries signal. But it is fitted on 7-term queries, and
**lexical score grows with query length while cosine does not** - lexical sums over matched terms
and fields, semantic is one bounded number. So the optimal additive weight is query-length
dependent, and no single constant is correct for a 3-term and a 20-term query.

**Change - evaluate three candidates, not one:**

| | approach | note |
|---|---|---|
| **A** | raise the constant | baseline. Cheapest, known to work at one query length, fragile across lengths. |
| **B** | normalise then blend: `w * cosine + (1-w) * (lexical / n_query_terms)` | puts both components on a per-term scale before combining. |
| **C** | reciprocal-rank fusion: `Σ 1/(k + rank_i)` over the lexical and semantic orderings | scale-free, discards magnitude entirely, immune to this whole class of bug. |

C is the same lesson the band produced independently: **the scale-free statistic won.** That is a
reason to take it seriously, not a reason to assume it wins here too.

**How the value is chosen.** Held-out split, stratified by **query length** (3 / 7 / 15 terms) -
that stratification is the point, because it is the axis A is expected to fail on. Extend
`labels.py::term_positives` to emit all three lengths.

**Metric.** `answer@1` and `answer@8` on paraphrase positives.

**Guards - the change is rejected if any fails:**

1. **`P_title` must not regress below ~95%** (currently 98%, n=120). Title queries are the case
   lexical gets right; if they degrade, semantic is now over-weighted and the fix has traded one
   failure for another.
2. **Negatives must not become answerable.** Re-run the 34 negatives; the top-8 must not start
   filling with plausible-looking wrong entries. Semantic similarity is exactly the mechanism that
   makes an off-topic entry *look* related.
3. **C, if chosen, breaks the band.** Rank fusion produces scores with no meaningful magnitude, so
   `top_over_median` would be computed over fused scores rather than match scores. F3 must be
   re-fitted after, never before.

---

## F2 - Recency weighting

**Problem.** `semantic_cache.py:1805`: `max(recency_floor, exp(-lambda_days * age_days))` with
`lambda_days=0.01`, `recency_floor=0.15`. Measured cost: **10 of 120** correct answers pushed out of
the top 8 (63 → 73 with recency off), 8.3 percentage points.

**The measured urgency is worse than the measured cost.** Corpus age today: median 21 days, max 80.
So the current spread is only **1.00 → 0.45, a 2.2× penalty**, and *nothing* is pinned at the floor.
It already costs 8.3 points at that mild setting. Past ~190 days entries hit the floor and the
penalty becomes **6.7×**. The damage grows as the archive ages, which is precisely backwards for a
decision archive - the entries recency punishes hardest are the settled decisions whose rationale is
least likely to be remembered and most valuable to retrieve.

**Change - evaluate four, including doing nothing:**

| | approach | effect |
|---|---|---|
| **A** | off for decision granularity | upper bound on the win; loses the tie-break entirely |
| **B** | raise the floor (0.15 → 0.5) | caps the penalty at 2× permanently, one-line, bounded forever |
| **C** | reduce lambda (0.01 → ~0.002) | half-life 69d → ~347d; still unbounded as the archive ages |
| **D** | recency as tie-breaker only - applied within a score band rather than as a global multiplier | principled: recency orders near-equals, it never overrides a clearly better match |

D is the shape that matches what recency is *for*. B is the cheap bounded version and the sensible
fallback if D proves fiddly.

**Guard - this is the one that matters.** The lifecycle set from F0. Recency is partly doing
supersession's job by accident; weakening it may surface retired decisions above their replacements.
Measure `head@1` and `head@8` on both `replaced_by` and `evolves` targets before and after. If
lifecycle regresses, the correct response is stronger explicit supersession damping, **not** keeping
a recency penalty that is silently doing the wrong job for the right reason.

**Second guard.** `_effective_lambda` already halves lambda for structural queries
(`semantic_cache.py:1798`). Whatever changes, that special case must stay coherent or be removed -
two overlapping recency mechanisms is how the current state arose.

---

## F3 - The relevance band

**Problem.** `retrieval.py:205`, `score >= 6.0 AND >= 0.55 * top`. On 34 negatives it flags "there
is an answer here" **34 times**: specificity 0.00 (95% CI 0.00-0.10), balanced accuracy 0.50 -
exactly chance. It carries no information.

The N-curve shows this is unfixable by retuning: a positive's score is invariant to corpus size
(17.962 at every N from 25 to 800) while the best *spurious* match climbs 19.1 → 27.8, so by 800
entries the average negative outscores the average positive's own answer. Re-fitting `top_abs`
optimally still only reaches 0.65.

**Change.** Replace the absolute floor with `top_over_median` (top score ÷ median of the top-k
scores). Held-out balanced accuracy **0.87 lexical / 0.85 semantic**, AUC 0.899 / 0.900, rejecting
every held-out negative, at a threshold near **1.22-1.32**. Consider blending `matched_frac`, which
is stronger below ~100 entries (AUC 0.894 at N=25, decaying to 0.837 at N=800, where
`top_over_median` is flat-to-rising).

**Two contract decisions this forces, which are not implementation details:**

1. **The statistic describes the query, not the result.** `top_over_median` is one number per result
   set. Today `relevance` is a per-row label. Either the band becomes a per-query "answerable" flag,
   or per-row labels are derived from the query-level verdict. Constitution §3 requires the rule be
   stated, not hidden, so `relevance_rule` in the payload must be rewritten to match whichever is
   chosen - and it is currently the only honest thing in that payload.
2. **Small result sets need defined behaviour.** With fewer than ~3 results the median is unstable
   and a single result gives `top/median = 1.0`, which classifies as "no answer". That is the
   small-corpus case, and it must be an explicit branch reporting *uncalibrated*, not an accident of
   the arithmetic.

**Ordering.** F3 is fitted **last**. F1 and F2 both change the score distribution any threshold
would be fitted against; fitting the band first means fitting it twice, and C in F1 would invalidate
it outright. Keep `relevance_calibrated: False` until F1 and F2 land.

---

## F4 - The process gap that produced all of this

**Problem.** Four constants shipped without validation - `RELEVANCE_FLOOR = 6.0`,
`RELEVANCE_STRONG_RATIO = 0.55`, the semantic weight `3.0`, `lambda_days = 0.01`. Every one, on
first real measurement, was wrong. That is not bad luck; constants were fitted against small
fixtures and never re-checked against the corpus that matters.

Today's standing check in `risk_signaling.md` catches *reporting* a clean result. Nothing catches
*shipping* an unvalidated constant.

**Change.** A registry test: every constant that affects ranking or banding must name the
measurement that set it and the date, or be explicitly marked `provisional`. The test fails if a
registered constant's value changes without its justification changing. Cheap to build, and it makes
the next unvalidated constant a test failure instead of a discovery six months later.

**Guard against making it theatre.** The registry must record the *measurement*, not a sentence. A
constant justified by "chosen to balance precision and recall" is exactly the state we are already
in.
