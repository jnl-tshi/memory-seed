---
title: Swarm reliability experiment — does splitting the axes help?
status: reference
---

# Swarm reliability experiment (2026-07-27)

Raised by JNL: *"do we benefit from separating the axes of the workers?"* — a question I had been
answering by assertion. This is the controlled comparison that settles it, plus the first iteration on
the brief that came out of it.

All arms ran **haiku** workers over the **same 39 entries in the same order** (`experiment-dev-set.tsv`,
every third row of the 116 single-area `memory-trace` entries). Raw per-worker answers are committed
beside this file so every number below is re-checkable.

## Why a control was needed

The three earlier cycles changed the brief **and** the worker at the same time, so the 81% cycle-1 to
cycle-2 agreement mixed two causes: did the brief improve, or did two workers simply roll differently?
Unanswerable as run. Every arm here holds the brief fixed and varies only one thing.

## Three measures, not one

| | question | how |
|---|---|---|
| **Reliability** | would we get this answer again? | 2 workers, same brief, same rows |
| **Validity** | is the answer right? | vs first-hand authored activity tags |
| **Coherence** | do the axes contradict each other? | area `trace-harness` paired with a non-test activity |

Validity's denominator is the 31 of 39 entries whose author wrote an activity slug. That is a biased
sample — entries whose authors bothered to tag are not random — and the earlier pilot adjudication
already found authored labels upheld only ~50% of the time when contested. Treat it as a proxy, not
ground truth. An adjudicated gold set is the missing piece.

## Experiment 1 — combined vs separated workers

**Arm A:** 2 workers, each assigning BOTH axes. **Arm B:** 2 area workers + 2 activity workers.
Identical slug definitions; the only difference is whether one worker answers both questions.

### Reliability

| | combined | separated |
|---|---|---|
| **area** | 87% | **97%** |
| **activity**, exact slug | **82%** | 54% |
| **activity**, collapsed to root | 85% | 85% |

### Validity (activity)

84%, 90% (combined) against 87%, 87% (separated) — **no meaningful difference.** Separation does not
make labels more correct.

### Coherence

| | violations |
|---|---|
| combined | 0 and 1 |
| separated | 2 and 2 |

**The combined workers produce FEWER violations, and that is the argument against them.** A single
worker holding both answers rationalises them into a coherent-sounding pair — one arm-A run produced
zero violations by deciding `trace-harness` + `process-correction` was fine. Independent workers, unable
to see each other, surfaced twice as many genuine mismatches. Coherence auditing is the one job where
independence is structurally required, and it is how the missing `testing` activity was found.

### The 54% was an artefact

Collapsed to the root, separated activity agreement is 85% — identical to combined. Of 18
disagreements, **12 were parent-vs-child of the same family** (`proposal-lifecycle` vs `roadmap`,
`bugfix` vs `process-correction`); only 6 were genuinely different categories. The workers agreed on the
concept and disagreed on how deep to go, because the brief said *"prefer a child slug where the evidence
supports it"* — which delegates depth to taste.

A brief defect, not an architectural one. Which made it testable.

## Experiment 2 — pin the depth rule

One variable changed. The instruction became a test the worker applies rather than judges:

> **Would filing this entry under a SIBLING of that child be plainly wrong?**
> If two siblings could each plausibly apply, use the parent.

with four worked examples taken from the observed disagreements. Everything else byte-identical. The
control arm is experiment 1's separated activity run — same rows, same model, minutes earlier.

| activity reliability | exact slug | root |
|---|---|---|
| control (old brief) | 54% | 85% |
| **treatment (depth rule)** | **82%** | **90%** |

Validity: 87% → 87–90%, i.e. unchanged. **+28 points of reliability at no cost in accuracy.**
Depth-only disagreements 12 → 3; genuine category disagreements 6 → 4.

## Conclusions

1. **Separate both axes.** Area is decisively better separated (97% vs 87%). Activity is now level
   (82% vs 82%) once the depth rule is fixed, so the earlier apparent penalty is gone. And coherence
   auditing only works with independent workers.
2. **Under-specified instructions cost more than architecture.** One sentence about depth was worth 28
   points — far more than any structural change measured here. Look for the vague instruction before
   redesigning the pipeline.
3. **Disagreement must be decomposed before it is diagnosed.** Raw 54% looked like a broken axis; split
   into depth-vs-category it was a solved problem and a smaller real one. Any future reliability number
   should be reported at both exact and root granularity.
4. **A control arm is cheap and non-optional.** Two extra workers turned "the brief probably helped"
   into a measured +28.

## What this does not establish

- No held-out set was used. The depth rule was written *after* seeing the disagreements it fixes, so 82%
  is an in-sample number and will be optimistic. It needs scoring once on the untouched 77 entries.
- Two workers per arm gives a noisy reliability estimate; three would give a majority label as well.
- Validity rests on authored tags, which are a proxy. The gold set remains the expensive missing piece.
- Only one coherence rule was tested (`trace-harness` implies a test-shaped activity). Others —
  `lifecycle-edges` implying a model activity, `NONE` area implying a process activity — are unwritten.
