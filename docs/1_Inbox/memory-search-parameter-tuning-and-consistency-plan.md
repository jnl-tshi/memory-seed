---
title: Memory Search Parameter Tuning and Consistency Plan
date: 2026-09-10
priority: proposed
next_action: Review the experiment scope and adoption gates before promoting to Todo.
---

# Memory search parameter tuning and consistency

Status: Inbox proposal for review. Creating this plan does not approve parameter changes or experiments.

## Outcome and expected uplift

Make equivalent searches behave consistently across supported interfaces, measure current retrieval
performance, then evaluate whether component score floors can reliably exclude irrelevant candidates. The practical aim is fewer missed decisions,
less time spent fetching context, and fewer confident answers when the memory contains no answer.
This improves Retrieval, Validation, Trust, and Application under the Constitution's five-question test.

The deliverable is a reproducible assessment with its limits, including a valid retain-current-settings
outcome. No globally optimal parameters or percentage improvement is promised before measurement.

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

## Phase 2 — Bounded evaluation of current condition and performance

Hold ranking weights and exclusion rules fixed after consistency is established. Measure the current
system before deciding whether improvement is needed. Success may be evidence that the current settings
are good enough; parameter changes are not a required outcome.

Use real questions and independently checked source answers. Include exact identifiers, paraphrases,
older valid decisions, superseded/evolved decisions, topic hierarchy, ambiguous requests, missing answers,
and plausible near-miss negatives. Score retrieval separately from agent conflict recognition or action.

Measure relevant-source recall at the actual result limit (also 1/5/8), irrelevant returned results,
per-query misses, current/retired ordering, p50/p95 latency, and returned context tokens. Inspect candidate
score distributions beyond the displayed top results: judging only what the existing ranker returns
would hide both missed relevant decisions and the population that later floors would exclude.
Unjudged candidates are unknown, not automatically irrelevant.

Pin code/corpus/sidecar hashes, provider and model version, embeddings, tokenizer, effective settings,
evaluation clock, seeds, query/label versions, and commands. Use the production corpus loader and
actual adapters. Confirm a deliberately degraded configuration changes an appropriate sensitivity
control before interpreting zero difference as equivalence. Freeze the clock only inside the harness.

Use a small pilot to assess labelling quality and run cost, then freeze a bounded evaluation population.
Group questions by source/decision lineage so paraphrases cannot leak between development and sealed
holdout sets. Previously inspected questions belong to development/regression material. Review labels
without seeing rankings or threshold proposals; use stronger independent review for ambiguous labels
and a sample of seemingly clear ones. Report agreement, adjudication, and uncertain cases.

Agree practical baseline adequacy criteria, sample size, and compute limits before scoring. For small
samples, report descriptive findings and uncertainty rather than unsupported general conclusions.
Numerical criteria remain to be selected during implementation planning.

Exit: a reproducible report of current performance, known weaknesses, sample coverage, and uncertainty.
Do not silently turn this baseline exercise into a broad weight sweep.

## Phase 3 — Evaluate component exclusion floors

Question: can individual query-to-decision component scores reliably identify irrelevant candidates?

A score floor is an exclusion threshold. A blend weight controls ranking contribution. The existing
RECENCY_FLOOR bounds an age multiplier; it is not a candidate filter. Start with lexical and semantic
scores. Age, popularity, or supersession alone do not establish query irrelevance and must not become
independent exclusion grounds through this experiment. Explicit authority selection and exact-reference
retrieval keep their existing contracts; score filtering must not silently discard mandated evidence.

Keep baseline ranking weights fixed. First evaluate each component separately, then compare only
justified combinations. Neither AND nor OR exclusion is preselected. Missing semantic scores during
fallback are unavailable evidence, not zero relevance. Record whether scores are raw, normalized, or
weighted, and keep that definition constant within each comparison.

Run in shadow mode: preserve normal results while recording what candidate floors would discard.
For each threshold report:
- irrelevant candidates removed and total candidate reduction;
- relevant decisions wrongly excluded, including per-query and critical-decision failures;
- changes to final recall, ordering, returned irrelevant results, and empty-result behavior;
- results by query type, corpus size, and provider/fallback mode;
- measured latency and token effects at the actual point where the filter would run.

Scoring all candidates before filtering cannot save that already-incurred scoring cost. Returning the
same number of similarly sized results may not save context tokens. Distinguish candidate reduction,
downstream work reduction, and user-visible benefit rather than treating them as equivalent.

Fit a bounded set of candidate thresholds on development data, with a declared trial count and stopping
rule. Freeze one candidate policy before opening the holdout. Compare against the consistent baseline
on the same queries. Failed or inconclusive holdout results mean retain baseline or obtain fresh data,
not repeat tuning against the holdout. Raw BM25F scales vary with query/corpus statistics; semantic
scores depend on model and representation. A universal floor is a hypothesis, not an assumption.
Consider normalization or scoped floors only if the simple approach fails for a demonstrated reason.

### Confidence and adoption evidence

Confidence intervals quantify uncertainty in measured rates such as relevant-decision loss; they do not
turn raw scores into per-result relevance probabilities. Use intervals appropriate to the sampling:
decisions within a query and paraphrases within a lineage are dependent, so avoid treating all
query-candidate pairs as independent observations. Predeclare the estimand, sampling unit, interval
method, and treatment of threshold selection.

Assess whether a floor's upper confidence bound on relevant-decision loss meets the agreed tolerance,
while its useful exclusion benefit meets the agreed minimum. Zero observed misses in a small sample
does not prove zero risk. If intervals are too wide, report insufficient evidence and price the
additional sample before expanding. Per-result confidence calibration is a separate possible follow-up.

Exit: recommend a supported floor policy, further bounded investigation, or no filtering change.
All three are valid outcomes. No reliable floor is preferable to a confident but unsupported exclusion.

## Adoption and follow-up boundary

Preserve the existing real-corpus ranking gate and fixtures. Any production filtering change requires
the frozen acceptance criteria, held-out evidence, adapter parity, meaningful negative controls,
relevant regression/full-suite checks, and a reviewed rollout/rollback plan. Retain the previous
parameter manifest and record the chosen policy and rationale in durable memory.

The first evidence claim is project-specific. Broader claims require another representative corpus.
Re-evaluate after material changes to corpus composition, scorer, model, chunking, or lifecycle
handling. Broad weight tuning, new ranking machinery, per-result confidence labels, and agent-task
replays remain separately justified follow-ups, not assumed work in this proposal.

## Capability allocation and execution sequence

This is the proposed allocation for future implementation, governed by the capability-allocation
contract in [agent collaboration](../../.memory-seed/skills/agent_collaboration.md).
Tiers describe requirements; actual model names and effort are recorded at dispatch.
No worker is launched by approving this document edit.

| Task | Depends on | Worker tier / effort | Review and acceptance |
|---|---|---|---|
| C1: inventory defaults and actual routes | None | Economy / medium | Orchestrator checks cited sources and coverage; no unsupported parity claims |
| C2: reproduce and correct discrepancies | C1 | Balanced / high | Independent frontier review; actual adapter parity and explicit-override tests |
| B1: freeze baseline protocol, labels, budget | C2 | Frontier / high | Independent frontier method review; production fidelity, sampling, and leakage controls |
| B2: implement bounded harness | B1 | Balanced / high | Independent frontier review of measurement logic and sensitivity controls |
| B3a: prepare and adjudicate labels | B1 | Economy / medium, frontier adjudication | Blind review of ambiguous labels plus a sample of clear labels; sealed data kept out of development |
| B3b: execute frozen baseline runs | B2, B3a | Economy / low or medium; scripts compute metrics | Validated harness and accepted labels; reproducible run receipts |
| B4: interpret baseline and scope floor experiment | B3b | Frontier / high | Report coverage, current performance, uncertainty, and justified scope |
| F1: freeze component-floor protocol | B4 | Frontier / high | Independent frontier review of loss tolerance, interval method, and holdout rules |
| F2: implement shadow evaluation | F1 | Balanced / high | Independent frontier review of exclusions, fallback, and protected evidence paths |
| F3: execute frozen sweeps | F2 | Economy / low or medium; deterministic scripts | Orchestrator verifies manifests, counts, failures, and complete outputs |
| F4: assess holdout and recommendation | F3 | Frontier / high | Independent frontier review; adopt, retain, or request more evidence with reasons |

The orchestrator owns stage transitions, scope, integration, and durable decisions. Normally use one
implementer and one independent read-only reviewer; parallelize only independent inventory or labelling
batches with disjoint ownership. Complete consistency before baseline measurement and baseline
interpretation before floor evaluation. Reviewers get evidence and the contract, not instructions to
confirm the author's recommendation.

### Parallelisation assessment

| Opportunity | Start and join conditions | Benefit and constraints |
|---|---|---|
| C1 interface inspections | Same pinned baseline and inventory format; reconcile all required routes before C2 | Independent read-only inspections may reduce elapsed time; use one worker if dispatch/context overhead dominates |
| B2 harness work alongside B3a labelling | B1 protocol and source population frozen; both accepted before B3b | Code and blinded labels can progress independently; keep labels away from threshold fitting and holdout access restricted |
| B3a label batches | Shared rubric and pilot pass; disjoint output ownership; all required adjudication before B3b | Parallelise by source/lineage without splitting it across development and holdout; preserve independent review |
| F3 frozen development sweep batches | F1 protocol and F2 harness passed; combine all outputs before candidate selection and F4 | Prefer deterministic script batching to extra agents; concurrent runs need immutable inputs and isolated outputs |

Timing/compute savings are unmeasured; the orchestrator sets a bounded concurrency limit at dispatch
from available slots, budget, memory and CPU contention. Benchmark latency in controlled serial runs
so parallel load does not distort comparisons. Holdout evaluation begins only after the candidate is
frozen; it is not another development batch. C2, B1, B4, F1, and F4 retain their evidence dependencies.
Reassess opportunities when coupling appears; a serial outcome is valid. No automatic scheduler is added.

Each dispatch gets a bounded packet with exact sources, allowed files, context allowance, execution
limit, return contract, and budget. Set numerical token/time/trial limits before launch after the pilot;
no unbounded provider calls or retry loops. Report estimates separately from observed usage.

Pilot economy assignments. Escalate to balanced for unresolved call paths or repeated mechanical errors;
to frontier for disputed meaning, statistical uncertainty, policy conflict, or a proposed scope change.
After two failed repair attempts on the same bounded assignment, return evidence to the orchestrator;
do not silently reset the retry counter, increase budget, or reduce review strength.
Actual model/effort availability and substitutions are checked before dispatch.

## Review decisions and acceptance checklist

Settled through discovery: consistency first; bounded baseline second; component-floor evaluation third.
Retaining current settings is a valid success. Filter combinations and numerical tolerances remain open.

- [ ] Configuration inventory and actual surface parity established.
- [ ] Baseline protocol, independent labels, budget, and split frozen.
- [ ] Current performance measured with uncertainty and production-path controls.
- [ ] Individual component floors tested in shadow mode before combination selection.
- [ ] Relevant-decision loss and useful exclusion assessed on held-out data.
- [ ] Confidence intervals interpreted at the correct sampling unit; inadequate evidence named.
- [ ] Adoption, no change, or further-study recommendation reviewed with scope and limitations.
- [ ] Every worker assignment has capability, review, budget, escalation, and dependency requirements.
- [ ] Parallel opportunities and serial constraints are assessed, with start/join conditions, resource limits, and cost justification.
