---
memory-system-version: 2.19
tags:
  - memory-seed
  - reference
  - topic-vocabulary
  - measurement
---

# Leg B: does per-decision topic attribution beat free inheritance?

> **Measured 2026-08-07.** Resolves the open question carried in
> [`write-time-sidecar-consolidation-proposal.md`](../2_Todo/write-time-sidecar-consolidation-proposal.md)
> and restated in
> [`write-time-topic-envelope-closure-proposal.md`](../2_Todo/write-time-topic-envelope-closure-proposal.md).
> **Verdict: yes, and by a wide margin. The backfill sweep is worth running.**

## Why it was open

The aborted pilot ran Leg A — scoring the swarm's attributions against authored
topics — and reported 0.613 agreement. That number was never safe to act on: if
both sides are model judgments, 0.613 is inter-annotator agreement rather than
accuracy, and nobody adjudicated who was right when they disagreed. Leg B, which
measures the campaign's actual *value*, never ran because Leg A gated first.

Leg B does not need Leg A settled, because it does not ask who is right. It asks
a structural question the corpus can answer on its own.

## Method

Two mechanical measurements over the corpus. No model calls; nothing here
depends on an LLM's opinion.

**1. Divergence.** For every entry where two or more decisions carry their own
attribution, compare each decision's own topic set against the entry-level
union — which is exactly what free inheritance would hand it.

**2. A permutation control.** Divergence alone proves only that the two models
*disagree*; an attributor that scattered an entry's topics across its decisions
at random would produce the same disagreement. So: does each decision's assigned
slug track that decision's own TEXT better than the same slugs reshuffled among
its siblings? Permutation is **within** an entry, holding the union, the decision
count, and the slugs-per-decision fixed. Only the pairing changes. Scoring is the
lexical overlap `topics suggest` already uses.

## Results

### Divergence — 208 entries, 563 decisions

| | |
|---|---|
| Entries where every decision got an identical set | 25 (12%) — keying added nothing |
| Entries where decisions differ | **183 (87%)** — inheritance over-attributes |
| Mean share of the entry union that is a decision's own | **0.572** |
| Median | 0.500 |

**Inheritance assigns a decision 42.8% topics on average that its own
attribution never claimed.** Over-attribution scales with entry size, which is
what you would expect if the effect is real:

| decisions in entry | entries | mean own-share | over-attribution |
|---|---|---|---|
| 2 | 111 | 0.648 | 35.2% |
| 3 | 59 | 0.557 | 44.3% |
| 4 | 29 | 0.479 | 52.1% |
| 5 | 6 | 0.381 | 61.9% |
| 6 | 3 | 0.689 | 31.1% |

The 6-decision row breaks the trend on **n=3 entries** and should not be read as
a reversal; the monotone 2→5 progression rests on 205 of the 208.

### Retrieval cost

Over these entries, a topic query returns 1,113 decisions under per-decision
attribution and 2,166 under free inheritance. **1,053 of 2,166 returned
decisions — 48% — would be false positives.** The slugs inheritance inflates
most are the broad activity axes: `feature-build` 162 → 289, `bugfix` 77 → 163,
`documentation` 45 → 120.

### Permutation control — 183 entries, 200 shuffles each

| | |
|---|---|
| Observed text↔topic overlap | 0.1727 |
| Shuffled overlap | 0.1473 |
| Lift | **1.17×** |
| Entries where the real assignment beat its own shuffled mean | **144/183 (78%)** |
| Sign test against 50% | z = 7.8 |
| Mean per-entry delta | **+0.0254 (95% CI +0.0204 to +0.0304)** |

The split is **not arbitrary**. A random carve-up would win half the time; the
real one wins 78%, and the confidence interval on the effect excludes zero by a
wide margin.

## Caveats, stated plainly

- **This does not resolve Leg A.** It shows per-decision attribution carries
  non-arbitrary information, not that any particular slug is the *correct* one.
  Those are different claims and only the first is measured here.
- **The definition of "what a decision is about" is the attributor's own
  output.** That is unavoidable for a corpus-internal measurement, and it is why
  the permutation control matters: it holds that output fixed and varies only
  the pairing, so a systematically-wrong-but-consistent attributor would still
  fail the control.
- **Lexical overlap understates.** Attribution is semantic; the proxy scores only
  shared word stems, so 1.17× is a floor on the true association, not an
  estimate of it. Direction and significance are unambiguous; the magnitude is
  not.
- The 6-decision bucket is n=3. See above.

## What follows

1. The topic-swarm backfill over the 201 decisions lacking decision-keyed
   Area+Activity is **worth running**. Inheritance is not a cheap approximation
   of keying — on multi-decision entries it is wrong about half the time a topic
   query touches them.
2. Write-time attribution matters more than backfill, because it is the only
   thing that stops the gap reopening. That is already closed
   (`write-time-topic-envelope-closure-proposal.md`).
3. Leg A remains unresolved and still gates any claim about attribution
   *accuracy*. Settling it needs adjudication of the disagreements, which is a
   human or a differently-designed exercise — not this one.

Reproduce: `leg_b.py` and `leg_b_permute.py` in the session scratchpad; both are
read-only over `.memory-seed/` and take no arguments beyond the repo root.
