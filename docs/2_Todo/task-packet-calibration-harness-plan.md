---
title: "Task Packet Calibration Harness Plan"
date: "2026-09-01"
project: "memory-seed"
status: "active"
priority: "P1"
next_action: "Freeze the representative development population and sealed holdout design now that the Qwen3.5 9B M0 plumbing gate has passed."
source:
  - "docs/4_Reference/model-tier-task-packet-budget-assessment.md"
  - "docs/4_Reference/clean-session-high-signal-task-packet-pilot.md"
  - "experiments/context-derivation/PREREGISTRATION.md"
  - "experiments/context-derivation/TERRA_SMOKE_FINDINGS.md"
scope: "Calibrate the value and operating limits of Memory Seed retrieval and compiled Task Packets across context conditions and model tiers."
non_goals:
  - "Do not change production retrieval, Retrieval Profile values, or budget thresholds from smoke data."
  - "Do not automate paid Claude subscription access or embed provider credentials."
dependencies:
  - "Delivered Task Packet compiler and six immutable v1 Retrieval Profiles."
  - "Hermes one-shot runner and LM Studio local inference server."
acceptance_criteria:
  - "A preregistered three-arm experiment runs from frozen task and packet artifacts."
  - "Tool use and provider usage are independently recorded where the execution surface exposes them."
  - "Development and holdout populations cover all six profiles and include missing and adversarial evidence."
  - "Profile and budget recommendations follow measured multi-model results rather than starting heuristics."
---

# Task Packet calibration harness plan

## Outcome

Build one provider-neutral, resume-safe calibration programme that separates the value of project memory,
the value of prepared Task Packets, and the capability of the subject model. It replaces ad hoc profile
number tuning with measured task-level evidence.

The five-question test: this work primarily improves **Validation** and **Retrieval**, and secondarily
**Trust** by requiring every scored conclusion to resolve to supplied or independently logged evidence.

## Pareto scope

The first useful 80/20 slice has three parts:

1. independent instrumentation at the actual retrieval boundary;
2. representative tasks across all six profiles with a genuinely sealed holdout; and
3. a compact adversarial set testing stale, conflicting, misleading, and instruction-like evidence.

Cross-project generalization, automatic profile routing, adaptive budgets, and drift automation follow
only after that baseline is trustworthy. Clause-targeted Constitution materialization is the first likely
token-efficiency follow-up because full-document inclusion can distort packet-size comparisons.

## Phases

### M0 — prove the harness

**Completed 2026-09-01 for plumbing only.** The three arms ran against Qwen3.5 9B, the tools arm made
independently audited Memory Seed calls, and the compiled arm used no supplemental retrieval. The smoke
also exposed Windows/Hermes transport and trust-annotation compatibility constraints, now handled and
recorded in `experiments/task-packet-calibration/M0_SMOKE_FINDINGS.md`.

- Reuse the deterministic Task Packet pilot corpus.
- Generate `no_memory`, `memory_tools`, and `compiled_packet` prompts from one task definition.
- Run one unscored Qwen3.5 9B cell through Hermes and LM Studio at a conservative context setting.
- Capture Hermes usage plus independent MCP calls and mechanically score the response.
- Treat any model-quality result as smoke evidence only.

### M1 — stabilize the evaluation population

- Reuse the 60 context-derivation queries, Run 12 misses, and prior adversarial fixtures where they remain
  valid, without reviving the retired harness architecture.
- Add representative tasks for implementation, bug investigation, research, ADR review, refactoring, and
  architecture.
- Keep lossy semantic summaries out of evidence; prior compression work showed material retrieval and
  fidelity regressions. Reduce context by selection while preserving canonical prose.
- Freeze development tasks, sealed holdout tasks, gold evidence IDs, corpus revisions, and task fingerprints.

### M2 — calibrate retrieval and packet quality

- Run paired three-arm trials per model and task.
- Fix recall failures before interpreting relevance bands or profile caps.
- Compare correctness, abstention, unsupported claims, retrieval calls, repeated reads, context use, and
  latency.
- Test profile selection separately from within-profile retrieval quality.

### M3 — calibrate profile values

- Explore bounded grids over related-decision depth, neighbouring sessions, maximum entries, evidence cap,
  Constitution granularity, and supplemental reserve.
- Select the smallest configuration that preserves task correctness and evidence grounding.
- Add new immutable profile versions only when the measured evidence supports them; never overwrite v1.

### M4 — calibrate model-tier budgets

- Hold the packet and task constant across local Qwen/Gemma and Claude Haiku/Sonnet/Opus runs.
- Use a common envelope for the primary comparison and separate context-size stress tests.
- Record provider usage and costs only when surfaced. Preserve the distinction between compiler estimates,
  provider input, output/reasoning, cached input, and price arithmetic.
- Define durable tier thresholds at reproducible quality changepoints, not at advertised context limits.

### M5 — independent validation and operation

- Run the sealed holdout once after the harness and candidate settings are frozen.
- Add cross-project validation before making general product claims.
- Define drift triggers for corpus growth, model/runtime changes, retrieval changes, or rising supplemental
  calls, each requiring a fresh calibration or holdout.
- Update the Retrieval Specification proposal, budget assessment, collaboration procedure, and roadmap with
  measured conclusions and explicit limitations.

## Current local execution facts

The verified local path is Hermes one-shot mode over LM Studio's local provider. Available Q4_K_M models
are Qwen3.5 9B, Qwen2.5 Coder 7B Instruct, and Gemma 4 E4B. Their catalogued maxima are not treated as
working budgets; the experiment pins the actually loaded context length and tests degradation below it.
Hermes exposes a usage-file surface, and its MCP configuration supports exact tool allowlists. The harness
uses a throwaway `HERMES_HOME`, no built-in toolsets, no inherited project rules, and only four read-only
Memory Seed tools.

Hermes 0.20.5 currently enforces a 65,536-token minimum local-model window in one-shot mode. That is a
runner constraint, not a claim that packets should approach 64K; the M0 compiled prompt used only 7,819
provider-reported input tokens including runtime and tool overhead.

Claude is a manual cross-provider track. The harness generates blinded prompt bundles and importable result
records; the user launches subscription runs. Missing token or cache telemetry remains unavailable.

## Decision gates

- Owner approval is required before the sealed holdout is opened or scored.
- Paid or externally metered model execution requires an agreed budget.
- Smoke failures may change the harness; holdout failures may not change the frozen experiment.
- No profile, retrieval, or budget production change follows directly from one model or one run.
