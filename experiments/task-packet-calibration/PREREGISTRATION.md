# Preregistration: reconstructable Task Packet calibration

Status: **DRAFT — development smoke only; scored calibration is blocked pending owner approval.**

## Question

How much do Memory Seed records and compiled Task Packets improve evidence-grounded task performance,
retrieval efficiency, and context use across less-capable local models and an independent Claude model
family?

## Primary comparison

Every task is run unchanged in three arms:

- `no_memory`: question only, with no Memory Seed evidence or retrieval tools;
- `memory_tools`: the same question with task-scoped, read-only Memory Seed tools but no prepared packet;
- `compiled_packet`: the same question with a deterministic compiled packet and the same fallback tools.

The first contrast measures the value of project memory. The second measures the additional value of
frontier-authored semantic dispatch plus deterministic selection and materialization.

## Subject families

- Local primary: Qwen3.5 9B, Q4_K_M, via Hermes and LM Studio.
- Local specialist: Qwen2.5 Coder 7B Instruct, Q4_K_M.
- Local economy: Gemma 4 E4B, Q4_K_M.
- Cross-provider validation: Claude Haiku, Sonnet, and Opus through manually launched subscription runs.

The exact model build, runtime version, configured context length, reasoning mode, and quantization are
pinned after unscored probes. Model results are reported separately and are never pooled into one quality
number.

## Task population

The final population will cover all six Retrieval Profiles: implementation, bug investigation, research,
ADR review, refactoring, and architecture. Each profile receives ordinary, missing-evidence, and adversarial
tasks. Adversarial cases include stale or replaced decisions, conflicting authority layers, misleading
lexical neighbours, malformed candidates, and instruction-like text inside evidence.

Development tasks are visible and may be rerun while building the harness. The holdout is authored by
Codex because Codex is not a subject model, then sealed before profile or budget tuning. Holdout questions,
gold answers, evidence IDs, corpus revision, and bundle fingerprints are frozen. A result-driven change
after opening the holdout creates a new experiment and requires a fresh holdout.

## Fairness and context

- The repository facts and task wording are identical across arms.
- The compiled packet's exact bytes are identical across subject models, though provider token counts may
  differ by tokenizer.
- The main comparison uses a common context envelope that fits comfortably inside every verified local
  runtime. Separate stress runs vary context size and are not mixed into the primary comparison.
- Silent truncation is a protocol failure. Context configuration and provider-reported usage are recorded.
- Temperature and sampling controls are pinned where the subject surface exposes them.

## Independent instrumentation

The harness records the actual MCP boundary: tool name, model-supplied arguments, pinned corpus, result
digest, result size, and returned semantic evidence IDs. It also records Hermes usage, wall time, model and
provider, packet and prompt fingerprints, process outcome, and raw response. Repeated retrieval of already
materialized IDs is scored as a packet-procedure failure.

Claude subscription runs use generated, blinded prompt bundles. When provider usage or tool telemetry is
not surfaced, the result records it as unavailable rather than estimating it from packet budgets.

## Mechanical outcomes

Primary:

- complete proposition correctness;
- evidence-ID resolution and support;
- correct abstention when evidence is absent;
- unsupported assertion count;
- repeated materialized fetches.

Secondary:

- retrieval calls and result characters;
- provider input, cached input, reasoning/output and total tokens when reported;
- output-to-input ratio, latency, and caller-supplied cost when available;
- performance by profile, model, arm, and context-size stress band.

## Analysis and stopping

- Use multiple repetitions and report variance; do not promote single-run deltas.
- Report per-task paired arm differences and per-model results with uncertainty intervals.
- Do not tune on holdout failures.
- Stop a subject queue on model/runtime/config drift, silent truncation, missing audit output, changed packet
  fingerprints, or an unavailable required tool.
- A profile threshold remains provisional until it is supported across representative tasks and at least
  one independent model family.

## M0 smoke gate

Status: **PASSED for harness plumbing on 2026-09-01.** See
[`M0_SMOKE_FINDINGS.md`](M0_SMOKE_FINDINGS.md). This does not change the DRAFT calibration status above.

Before expanding the population, one Qwen3.5 9B development task must prove:

1. all three prompts are generated from one task and one pinned corpus;
2. the compiled packet reconstructs deterministically;
3. only the two Memory Seed arms expose the four read-only tools;
4. tool calls are logged independently;
5. Hermes reports the local model and usage without cloud-provider credentials;
6. the answer is mechanically scoreable; and
7. no packet content is silently truncated.

Passing this gate validates the harness plumbing only. It is not evidence for profile or model-tier values.
