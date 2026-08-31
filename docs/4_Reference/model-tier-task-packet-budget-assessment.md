---
title: Model-tier task-packet budget assessment
status: reference
date: 2026-08-27
decision_status: accepted-provisional-baseline
sources:
  - ../../.memory-seed/skills/adr_sweep.md
  - ../../.memory-seed/skills/end_of_turn.md
  - ../2_Todo/link-audit-decision-judgment-swarm-proposal.md
  - https://developers.openai.com/api/docs/models
  - https://developers.openai.com/api/docs/models/gpt-5.6-terra
  - https://platform.claude.com/docs/en/models/overview
  - https://platform.claude.com/docs/en/build-with-claude/context-windows
  - https://platform.claude.com/docs/en/models/sonnet-5/whats-new-sonnet-5
  - https://arxiv.org/html/2601.02023
  - https://huggingface.co/datasets/openai/mrcr
---

# Model-tier task-packet budget assessment

## Outcome

JNL accepted the following provisional starting budgets on 2026-08-27. They govern the prepared
**task packet** given to one worker: instructions, candidate evidence, retrieved decision history,
tool/schema material, and working headroom. They are not claims about the model's advertised context
window or a universal reasoning limit.

| Capability tier | Representative current models | Starting target | Soft cap | Shard threshold |
|---|---|---:|---:|---:|
| Economy | Claude Haiku 4.5 / GPT-5.6 Luna | 16K | 24K | 32K |
| Balanced | Claude Sonnet 5 / GPT-5.6 Terra | 32K | 48K | 64K |
| Frontier | Claude Opus 5 / GPT-5.6 Sol / Claude Fable 5 | 64K | 96K | 128K |

The thresholds mean:

- **Starting target:** the normal prepared packet. Retrieval should aim to fit here without dropping
  answer-bearing evidence.
- **Soft cap:** first run deterministic deduplication and remove demonstrable distractors. If the
  packet remains above this boundary and the work is separable, prefer Level 2 partitioning.
- **Shard threshold:** do not send the packet to one worker by default. Partition it or deliberately
  select a higher tier and record why the larger single-context synthesis is necessary.

These are powers-of-two operating bands for predictable routing, not measured change-points. They
remain provisional until a Memory Seed-specific benchmark measures answer quality over real sweep
packets.

## Why 32K is not universal

The earlier ADR-sweep decision used `20 unresolved candidates` as the Level 2 fan-out threshold. Its
reason was coordination economics: one context preserves consistency for a small queue, while the live
96-item queue was large enough to earn bounded read-only fan-out. It did not measure candidate size,
packet tokens, evidence density, or a model-specific inference elbow.

Likewise, 32K is useful for the economy tier because it leaves a small worker substantial room to
reason over a curated packet. It is not a limit shared by larger models. Current Sol and Terra models
advertise 1.05M-token windows; current Sonnet, Opus, and Fable models advertise 1M-token windows. The
larger tiers can therefore accept more evidence without approaching their request limits. That justifies
raising their operating bands, but not scaling packet size linearly with the advertised window.

Large windows measure what an API accepts. Sweep quality depends on whether the model can distinguish
similar decisions, retain their ordering and authority, and synthesise dispersed evidence. More context
also increases distraction, latency, and cost. The routing target is therefore the smallest sufficient
packet, not the largest request the provider permits.

## Evidence and its limits

### Haiku provides the clearest warning against treating capacity as quality

Anthropic documents a 200K-token window for Claude Haiku 4.5. An independent 2026 long-context study
tested it in 10% increments up to approximately 175K tokens. Logical-inference accuracy averaged 58.5%
over the sweep and was 48% at the tested capacity; inference around middle-context placements fell to
approximately 50%, and several ten-fact distributed layouts produced 0-20% logical inference.

The study does **not** publish a numeric result for every length point, so it does not establish a
defensible single elbow. The economy 16K/24K/32K band is consequently a conservative operating policy,
not a result reported by that paper.

### MRCR measures discrimination, not general logical synthesis

MRCR means Multi-Round Coreference Resolution. In the eight-needle form, a synthetic long conversation
contains eight identical requests with different assistant responses. The final prompt asks for one
ordinal occurrence, such as the sixth response. The score is a text-match ratio against that exact
response.

This is relevant to ADR and ESR work because many decisions use similar vocabulary and must be
distinguished by occurrence and context. It does not test the full sweep problem: connecting several
facts, applying authority rules, detecting decision-chain gaps, and producing a recommendation. MRCR
results may support a model choice, but cannot set Memory Seed's packet threshold by themselves.

### Current larger-model documentation establishes capacity, not an elbow

Official model documentation establishes the current windows and model roles, but does not publish a
task-packet change-point for Memory Seed-style decision synthesis. The balanced and frontier bands are
therefore engineering defaults chosen to:

1. give stronger models more useful evidence than economy workers;
2. keep substantial distance from the nominal one-million-token limit;
3. preserve a simple doubling relationship between routing tiers; and
4. force explicit partitioning before a packet becomes an indiscriminate corpus dump.

OpenAI also applies higher pricing to Terra requests above 272K input tokens. This is not the quality
boundary, but it reinforces keeping routine packets far below the full context window.

## Token counting and cross-model comparability

Token counts are model-specific. Anthropic states that Sonnet 5's tokenizer produces approximately 30%
more tokens for the same text than Sonnet 4.6, with the exact change depending on the workload. A packet
called `32K` under one tokenizer therefore need not contain the same text as `32K` under another.

Recommended implementation:

- use a lightweight built-in estimate for offline queue planning and early routing;
- attach a safety margin and identify the estimator/model family used;
- use the provider's native token-counting endpoint or tokenizer immediately before dispatch when it is
  available;
- never add a network dependency to the Memory Seed core merely to estimate packet size; and
- record the actual provider-reported input count in benchmark results so estimates can be calibrated.

The lightweight estimator is deliberately approximate. It exists to choose a routing band without a
provider call, while the provider count remains authoritative for request fit and experimental evidence.

## Consequences for ESR and ADR sweeps

Candidate count should no longer be the primary orchestration signal. The sweep should calculate or
estimate the complete prepared packet for the selected **worker** tier:

1. assemble the candidate instructions and evidence;
2. estimate its tokens using the best available model-specific counter;
3. compare it with the selected worker tier's target, soft cap, and shard threshold;
4. use decision-chain coupling and clean domain separability as independent reasons to escalate; and
5. retain the existing `20 candidates` rule only as a compatibility fallback when no estimate is
   available.

The orchestrator's capability does not raise a leaf worker's limit. A Sol orchestrator may reconcile a
larger final synthesis packet, but a Haiku worker still receives no more than an economy-tier shard.
Fan-out changes review capacity, never authority: workers remain read-only, the orchestrator reconciles
recommendations, and the user approves every ADR mutation.

## Benchmark required before durable locking

Run a provider-counted Memory Seed benchmark rather than extrapolating from generic long-context tests.
At minimum, score real ADR/ESR candidate packets at:

- economy: 8K, 12K, 16K, 24K, 32K, 48K, and 64K;
- balanced: 16K, 24K, 32K, 48K, 64K, 96K, and 128K; and
- frontier: 32K, 48K, 64K, 96K, 128K, and at least one larger diagnostic point.

Measure candidate recall, reference correctness, recommendation agreement with adjudicated gold,
unsupported assertions, latency, provider-reported input/output tokens, and cost. Include dispersed
decision chains, misleadingly similar candidates, middle-position evidence, and negative controls where
required evidence is absent.

The durable threshold should be the last size before a reproducible material degradation in sweep
quality, not a fixed percentage of the provider's context window. Until that benchmark exists, the table
above is the accepted provisional routing baseline.

## Sources

- [OpenAI current model catalogue](https://developers.openai.com/api/docs/models)
- [GPT-5.6 Terra specifications and long-request pricing](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- [Anthropic current model overview](https://platform.claude.com/docs/en/models/overview)
- [Anthropic context-window documentation](https://platform.claude.com/docs/en/build-with-claude/context-windows)
- [Anthropic Sonnet 5 tokenizer note](https://platform.claude.com/docs/en/models/sonnet-5/whats-new-sonnet-5)
- [Not All Needles Are Found](https://arxiv.org/html/2601.02023)
- [OpenAI MRCR dataset and scoring description](https://huggingface.co/datasets/openai/mrcr)
