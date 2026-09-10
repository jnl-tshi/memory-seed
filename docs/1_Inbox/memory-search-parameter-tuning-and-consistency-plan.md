---
title: Memory Search Parameter Tuning and Consistency Plan
date: 2026-09-10
priority: proposed
next_action: Review the experiment scope and adoption gates before promoting to Todo.
---

# Memory search parameter tuning and consistency

Status: Inbox proposal for review. Creating this plan does not approve parameter changes or experiments.

## Outcome and expected uplift

Make equivalent searches behave consistently across supported interfaces, then measure which settings
find useful project memory with fewer irrelevant results. The practical aim is fewer missed decisions,
less time spent fetching context, and fewer confident answers when the memory contains no answer.
This improves Retrieval, Validation, Trust, and Application under the Constitution's five-question test.

The deliverable is a reproducible parameter recommendation with its limits, not a claim of universally
optimal settings. No percentage improvement is promised before measurement.

## Starting evidence

Source baseline: main commit `3b4173c470666dd96972007631e158fdf9e675b2`, inspected 2026-09-10.
Recheck the baseline before implementation; this document is a dated observation.

- `memory_seed/semantic_cache.py` declares `RECENCY_FLOOR = 0.98`; the public library path in
  `memory_seed/retrieval.py` inherits it. `memory_seed/mcp_server.py` advertises and supplies `0.15`.
  This is a confirmed source discrepancy; reproduce its end-to-end consequences before fixing it.
- Decision `mse_hqasfw7847m20vz4:d3` in the
  [2026-08-05 session](../../.memory-seed/sessions/2026-08/2026-08-05.md) deliberately made recency a
  tie-breaker. Age alone should not outweigh relevant older decisions; lifecycle edges carry currency.
- Semantic blending and BM25F were previously measured and adjusted. Existing values are a baseline,
  not arbitrary placeholders to sweep from scratch. The earlier semantic weight of 60 preceded the
  BM25F refit to 15; do not transplant results between scoring scales.
- [Calibration findings](../../experiments/band-calibration/FINDINGS.md) explicitly withdraw some
  early results: the harness omitted sidecar lifecycle state and did not use production ranking flags.
  Only findings that survive those corrections may motivate new experiments.
- The [history retrieval skill](../../.memory-seed/skills/history_retrieval.md) marks relevance bands
  uncalibrated. `strong` and `no_match_above_threshold` cannot currently establish answerability.
- The [real-corpus ranking gate](../5_Completed/real-corpus-ranking-validation-gate-proposal.md)
  already requires fixtures plus real-corpus A/B evidence before ranking defaults change.
- The [2026-08-10 session](../../.memory-seed/sessions/2026-08/2026-08-10.md), including
  `mse_28eqx7r4zhfe6cah:d1`, records sealed, source-disjoint evaluation and production-path checks.

## Scope and reuse

Cover core/library search, CLI, MCP, and any Trace, profile, or Task Packet consumer that actually
invokes the same search path. Explicit selectors are a different contract and need not produce the
same ranked output. Inventory the real call paths before assigning parity expectations.

Reuse the existing corpus loader, ranking A/B tooling, calibration experiments, and test fixtures.
Reconcile remaining work in [retrieval recall fixes](retrieval-recall-fixes-proposal.md) and the
decision-level ranking gate before building another harness. Coordinate with the
[Task Packet calibration plan](../2_Todo/task-packet-calibration-harness-plan.md) and
[evidence-first retrieval plan](memory-seed-evidence-first-governed-retrieval-plan.md): this proposal
owns search configuration and ranking evidence; those plans own their broader packet/delivery claims.

Non-goals: embedding-model training, a new search engine, automatic production tuning, new authority
rules, rewriting historical memory, or implementing the wider Superpowers workflow.

## Phase 1 — Audit and establish a consistent baseline

1. Record each surface's advertised defaults, actual supplied values, config/profile overrides,
   validation, provider/fallback behavior, granularity, filters, and cache use. Include semantic weight,
   recency floor/decay, BM25F field weights and length normalization, lifecycle damping/successor lift,
   attention opt-in, result limit, and relevance thresholds wherever applicable.
2. Build a small parity matrix using identical corpus revision, query, effective configuration,
   provider, date, and granularity. Compare ranked identities and score components through actual
   adapters, allowing only documented presentation differences and numeric tolerance.
3. Test omitted parameters, explicit defaults, explicit overrides, zero/false values, invalid values,
   semantic fallback, and cold/warm caches. Inspect documentation and seeded examples for stale values.
4. Reconcile discrepancies against current authority and the recorded rationale. Where shared behavior
   is intended, use one owned default/resolver and tests that prevent adapter drift. Preserve intentional
   explicit overrides. Review the recency correction as observable behavior, including age/lifecycle cases.
5. Freeze the corrected, verified baseline separately from experimental tuning. Record before/after
   outputs and effective settings, so repairing drift is not mistaken for a tuning gain.

Exit: every relevant surface either agrees or has a documented, tested reason to differ. Unknown or
unverified routes remain visible and prevent a claim of complete parity.

## Phase 2 — Freeze a credible evaluation

Use real questions and independently checked source answers. Include exact identifiers, paraphrases,
older still-valid decisions, superseded/evolved decisions, topic hierarchy, ambiguous requests, missing
answers, and plausible near-miss negatives. Include relevant Constitution/ADR/decision lookup tasks,
but score retrieval separately from whether an agent recognises a conflict and acts correctly.

Group all questions and paraphrases for the same source or decision lineage into one split. Keep a
development set for tuning and a sealed holdout for the final candidate. Previously inspected examples
are development/regression material, not fresh holdout evidence. Review labels before seeing rankings;
an LLM may draft labels but cannot be the sole judge of its own results.

Pin code, corpus and sidecar hashes, provider/model version, embeddings, tokenizer, effective settings,
evaluation clock, seeds, query/label versions, and commands. The harness must use the production corpus
loader and adapters; prove a deliberately degraded configuration worsens an appropriate sensitivity
control before interpreting a zero difference as equivalence. Freeze dates only in the test harness.

Before running the sweep, agree a primary metric, minimum worthwhile gain, tolerated regressions,
no-answer error ceiling, sample size, and compute cap. Proposed primary metric: relevant-source recall
at the actual default result limit, also reported at 1/5/8. Choose sample size from the desired detectable
gain and uncertainty; a small pilot is descriptive if it cannot support that conclusion.

## Phase 3 — Tune within a bounded budget

Start with local, deterministic runs and cached embeddings. Profile cost before any model-assisted
evaluation; require a separate budget for network/provider calls. Run a small coarse sweep around
current settings, one parameter family at a time, then only justified interactions. Record trial count
and stopping rule. Avoid an exhaustive Cartesian grid or a new model by default.

Measure recall@k, first relevant result rank (MRR), ordering quality where graded labels exist (nDCG),
current-versus-retired decision behavior, and false answerable/no-answer errors. Report per-query wins,
losses, subgroup sizes, paired uncertainty intervals, and repeated-selection effects. Measure p50/p95
latency and retrieved context tokens on identical hardware; mark actual provider cost unavailable unless
measured. For equivalent results, prefer the simpler configuration and lower measured cost.

Recency changes must preserve older valid decisions. Lifecycle ranking cannot grant authority, erase
historical decisions, or silently change explicit filter semantics. Keep attention opt-in unless it
independently passes the existing ranking gate.

## Phase 4 — Calibrate relevance and test the final candidate

Calibrate answerability separately after ranking is frozen. Compare current labels with simple candidate
rules and an explicit uncalibrated outcome. Test realistic missing-answer and near-miss questions across
corpus sizes and semantic/fallback modes. Select thresholds on development data; report false positives
and false negatives with sample counts and uncertainty. If discrimination is inadequate, retain the
uncalibrated flag and content-based judgement rather than claiming the band is trustworthy.

Open the sealed holdout once for the selected candidate versus the corrected baseline. A failed or
inconclusive result means retain baseline, narrow the claim, or design a new experiment with fresh data;
do not tune repeatedly against that holdout. Use another representative project before claiming general
defaults are better across projects. Without it, label the result project-specific.

Optionally replay a small frozen set of agent tasks with baseline/candidate context, using the same
model/settings and repeated runs. Measure cited decision use, conflict recognition, unsupported claims,
and task completion separately. Ranking improvement alone does not prove faster delivery or safer action.

## Phase 5 — Adopt, verify, and retain rollback evidence

Publish the parameter manifest, commands, labelled dataset/split hashes, per-query results, confidence
limits, rejected candidates, and remaining gaps. Adoption requires the predeclared gain and regression
limits, meaningful negative controls, production parity, fixtures, and the existing real-corpus gate.
If no candidate clears those gates, retaining current parameters is a successful evidence outcome.

After approval, land a bounded change with meaningful adapter/regression tests and relevant full-suite
checks; record the chosen values and rationale in durable memory. Update affected docs/examples and
release notes. Preserve the previous parameter manifest and a tested rollback path. Re-evaluate after
material changes to corpus composition, provider, scorer, chunking, or lifecycle handling rather than
silently adapting values during normal searches.

## Decisions at review

| Decision | Proposed starting position |
|---|---|
| What happens first? | Confirm and repair surface drift, then freeze the tuning baseline. |
| What does success mean? | Better relevant-source recall within agreed regression and cost limits. |
| How much compute? | Bounded local sweeps first; price a pilot before allocating model calls. |
| What is the evidence boundary? | Production-path tests plus an untouched holdout; broader claims need another project. |
| What if relevance bands remain weak? | Keep them explicitly uncalibrated. |
| What gets approved now? | Review of this inbox plan; implementation and numerical acceptance gates remain to be agreed. |

## Completion checklist

- [ ] Source-backed configuration inventory and tested surface parity.
- [ ] Corrected baseline, independent labels, frozen protocol, budget, and sealed split.
- [ ] Bounded experiment report with per-query regressions and reproducible commands.
- [ ] Separate relevance/abstention verdict, including failed or inconclusive outcomes.
- [ ] Evidence-backed adoption or retain-baseline decision with scope and limitations.
- [ ] If adopted: integration checks, durable decision, documentation, and rollback evidence.
