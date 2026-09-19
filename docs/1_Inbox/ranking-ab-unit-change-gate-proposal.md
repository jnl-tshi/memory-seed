---
title: "Ranking-AB Unit-Change Gate Proposal"
date: "2026-08-05"
project: "memory-seed"
status: "proposed; not built"
priority: "P2"
next_action: "Decide whether unit changes need a gate at all, or whether the real-corpus measurement harness is the right instrument for them."
related:
  - "docs/CONSTITUTION.md"
  - "docs/7_Replaced/attention-retrieval-signal-proposal.md"
  - "docs/5_Completed/memory-index-dry-run-plan.md"
  - "docs/5_Completed/real-corpus-ranking-validation-gate-proposal.md"
---

# Ranking-AB Unit-Change Gate Proposal

## Why this exists

On 2026-08-05 the default retrieval granularity changed from `entry` to `decision`. That change did
not pass through `memory-seed ranking-ab`, and the first reading of that fact was that a gate had
been skipped.

It had not been. The gate **structurally cannot express a change to the retrieval unit**, and
discovering that is the finding this document records. `ranking-ab` is a gate over *boolean signal
flips* — freshness on/off, supersession damping on/off — evaluated against a fixed corpus. A
granularity change alters the corpus itself, which is the one thing every part of the comparison
assumes is constant.

This is not an argument that the change was unvalidated: it went through the dry-run harness
(71.0 → 96.8) and the real-corpus measurement in `experiments/decision-retrieval-scale/`. It is an
argument that the *gate* has a documented blind spot, and that anyone reaching for it to validate a
future unit change will find it silently unable to do the job.

## The three structural blocks

Each is a specific line, not a design opinion.

**1. The corpus is extracted once, before the arms split, with the unit hardcoded.**
`ranking_ab.py:466` reads `corpus = extract_memory_chunks(path, granularity="entry")`. Both arms
then receive that same list. There is no seam at which arm A could hold entry chunks and arm B
decision chunks.

**2. The granularity argument is dead on this path anyway.** `_rank` (`ranking_ab.py:310-321`)
always passes `chunks=list(corpus)` into `rank_session_memory`, and when `chunks=` is supplied the
granularity keyword is never consulted (`semantic_cache.py:278`). So even passing a granularity
through would change nothing — a trap worth naming, because it fails silently rather than raising.

**3. The comparison is keyed on `entry_id`, which decision chunks share.** `_compare_query` builds
its rank and score maps as `{r.chunk.entry_id: ...}` (`ranking_ab.py:388-392`). Several decision
chunks from one entry carry the same `entry_id`, so the dict comprehension keeps whichever sorted
last and silently discards the rest. The comparison would run, report numbers, and be meaningless —
exactly the silent-failure-toward-a-clean-result shape recorded in `risk_signaling.md`.

## The block that matters most

Even with all three fixed, **the no-hit control cannot exist for a unit change.**

`passed` requires that queries which touch nothing affected rank identically under both arms
(`ranking_ab.py:115-139`). That control is the gate's defence against a signal that quietly
perturbs unrelated results. It works because a boolean signal affects a *subset* of entries.

A unit flip affects **every** entry — there is no unaffected remainder to hold still. So
`signal.affected()` returns everything, the control bucket is empty, and `requires_no_hit_control`
either fails permanently or must be waived. Waiving it removes the only thing making the pass
meaningful, which is the same vacuous-approval failure that `requires_affected_hits` was added to
close for the attention signal.

## What building it would take

If a unit-change gate is wanted, the minimum honest shape is:

- **Per-arm corpus factories.** `Signal` gains an optional `corpus_for(arm)` so each arm extracts
  its own chunks; `run_ab` stops extracting once up front.
- **Chunk-id keyed comparison.** The rank maps key on a stable chunk identity rather than
  `entry_id`, with `entry_id` retained for display and roll-up. This is the largest change and it
  touches `RankChange`, the report formatter, and every existing signal's expectations.
- **Drop the `chunks=` pin in `_rank`**, or make `rank_session_memory` raise when both `chunks=` and
  a non-default granularity are supplied, so the dead-argument trap cannot recur.
- **A replacement for the no-hit control.** The candidate is *lineage stability*: for queries whose
  correct answer is derivable from lifecycle structure (a superseded decision's title should surface
  its `replacing_head`), the answer must not change across the unit flip even though the ranks do.
  That tests the property a unit change should preserve, rather than a property it necessarily
  violates.

## Recommendation

**Do not build this yet.** The last bullet is the real work and it is unproven: whether lineage
stability is a strong enough control to make a unit-flip pass mean anything is itself a research
question, and inventing a weaker control to unblock a gate would produce a green light that
certifies nothing.

The measurement harness in `experiments/decision-retrieval-scale/` already answers the practical
question a unit change raises — band distribution, token cost, and top-1 lineage stability on the
real corpus — without pretending to be a pass/fail gate. The honest position is that unit changes
are validated by measurement and judged spot-checks, and that `ranking-ab` covers signal flips only.

What should change now is the **documentation**, not the code: the gate's own help text and the
signal registry should say what it does not cover, so the next agent does not reach for it, get a
green result from a comparison keyed on colliding ids, and believe it.
