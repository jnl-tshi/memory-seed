# Preregistration: ADR context derivation

Status: **APPROVED**

Approved by JNL on 2026-08-04 after review of the twelve frozen questions,
task manifest, and candidate gold definitions.

Base revision: `f11a5dcb453f1a160864a10c7c5a1ee81ade0e48`.

The frozen answer contract reports ADR status explicitly and keeps `related`
supporting edges separate from `evolves`/`replaces` lineage edges. This prevents
prose-only inference from masking an authority or edge-typing error.

## Question

Which deterministic context policy gives Claude and Codex the smallest packet
that still preserves accepted ADR authority, necessary decision lineage,
typed lifecycle links, source evidence, and honest absence?

## Frozen population

- Twelve tasks: six from the three live ADRs and six adversarial fixtures.
- Four arms: `search-mcp`, `retrieval-v1-packet`,
  `adr-candidate-packet`, and `adr-mcp-workflow`.
- Three repetitions per task/arm/agent.
- Agents: Claude and Codex, reported separately and never pooled.
- Subject runs: `12 * 4 * 3 * 2 = 288`.
- Schedule seed: `20260804`.
- Maximum subject concurrency: three per agent and six total.
- Frozen judge-selection manifest: `JUDGE_SELECTION.json` (96 cells).
- Observed CLI versions before model probes: Claude Code `2.1.221`; Codex
  `codex-cli 0.146.0`. Exact model IDs remain pending unscored probes and are
  therefore deliberately unfrozen in `LIVE_MATRIX.json`.

## Offline selection rule

Every strategy is resolved twice at the same corpus revision. A strategy is
ineligible if any task lacks a required ADR, decision, or lifecycle edge; if
accepted head/status is wrong; if `related` is promoted to lineage; if an
expected absence is not explicit; or if selection order/fingerprint changes.

Eligible strategies are deduplicated by normalized strategy fingerprint. The
ADR grid uses a bounded factorial for the structural axes plus explicit pairwise
probes for all pending/rejected/no-change combinations and every item/token
budget pairing; it is not an uncontrolled million-cell full factorial. The
Pareto frontier is computed over irrelevant token proxy, total token proxy,
and latency. The live candidate is chosen lexicographically by:

1. lowest total irrelevant-token proxy;
2. lowest total token proxy;
3. lowest p95 latency;
4. stable strategy fingerprint.

There is no composite quality score.

## Live arms

1. `search-mcp`: fixture MCP exposes only `memory_search` and
   `memory_get_chunk`.
2. `retrieval-v1-packet`: a materialized current v1 Retrieval Spec pack is
   supplied inline; no repository or MCP access.
3. `adr-candidate-packet`: the frozen ADR-aware candidate pack is supplied
   inline; no repository or MCP access.
4. `adr-mcp-workflow`: fixture MCP exposes the existing read-only ADR,
   Retrieval Spec, search, and chunk tools; no write tool is listed.

Using direct filesystem retrieval or an undeclared tool is a protocol failure,
not an exclusion. A run is replaced only for a recorded harness failure,
provider outage, or timeout under the frozen top-up rule; substantive model
failures remain in the denominator.

## Primary gates

A production recommendation requires all of:

- zero accepted-head or status errors in `adr-candidate-packet`;
- at least 90% complete task correctness for each agent separately;
- every material citation resolves to included evidence;
- every missing-evidence task abstains correctly;
- no `related` edge is classified as lineage;
- candidate accuracy is not below `retrieval-v1-packet` and median context is
  at least 50% smaller;
- `adr-mcp-workflow` accuracy is within five percentage points of
  `adr-candidate-packet` for each agent;
- no gold leakage, parent-runtime write, incomplete shard, configuration
  change, or unrecorded exclusion.

## Secondary review

One repetition per task/arm/agent cell is selected from the schedule before
results exist, producing 96 blind explanation reviews. Claude judges Codex and
Codex judges Claude. Mechanical identity, edge, citation, and abstention scores
remain authoritative; model judgement cannot override them without a recorded
manual adjudication.

## Stop and reporting rules

- Freeze the candidate fingerprint before the first live run.
- Pin and record CLI/model versions after unscored smoke probes.
- Stop an agent queue on a mid-trial model/configuration change.
- Report Wilson intervals, task failures, token/cost/latency distributions,
  tool sequences, context utilization, and every exclusion per agent.
- Do not change production retrieval, MCP, Evidence Pack, ADR, or ranking
  behavior from these results without a separate owner approval.
