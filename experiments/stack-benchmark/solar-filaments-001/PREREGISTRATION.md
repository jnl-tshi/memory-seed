# Preregistration — Solar Filaments Stack Benchmark 001

Status: **DRAFT — pilots blocked until `benchmark.json` is FROZEN.**

## Question and population

Does Memory Seed improve the quality, context recovery, decision provenance, or
agent effort of a Claude engineering run, alone and alongside ICM, Graphify, or
Semble? The workload is Kaggle's Solar Filament Segmentation Challenge 2026.
One unscored pilot per arm validates the instrument; no stack conclusion may be
drawn until a later preregistered repeated run.

Arms are `baseline`, `icm`, `memory-seed`, `graphify`, `semble`,
`memory-seed-icm`, `memory-seed-graphify`, and `memory-seed-semble`.

## Constants

- Same frozen source commit, data hashes, prompt, Claude model/CLI, permissions,
  validation split, local evaluator, capability envelope, and submission schema.
- Treatments are prepared before the engineering clock starts. Setup time/cost is
  reported independently.
- Graphify uses deterministic code extraction plus LLM-assisted analysis of
  notebooks, Markdown, configuration, and supplied competition documentation.
- Semble indexes code only with a fresh run-local cache.
- Strict per-arm MCP allowlists are measured before launch. User-level connectors
  or undeclared tools invalidate the run.

## Clock contract

Four disjoint classifications are recorded as timestamped half-open intervals:

1. `agent_active`: reasoning, local tools, edits, result inspection and decisions.
2. `compute_wait`: Colab queue/training/validation/inference; excluded from agent efficiency.
3. `treatment_setup`: ICM generation, Memory Seed init, Graphify extraction, Semble indexing.
4. `end_to_end`: derived from first start to terminal event and never scored.

Intervals within one class are unioned so overlap cannot double-count. Active and
compute-wait intervals may overlap; each retains its own duration. A run is invalid
if an event labels the same interval as both `agent_active` and `compute_wait`.
GPU model, CUDA, RAM, utilization, interruptions and runtime duration are diagnostic
covariates only. Changing simulated GPU duration must not change quality or agent
efficiency.

## Outputs and scoring

Every run owns `source/`, `working/`, `submission/`, `final-report.md`,
`decisions.md`, `run-log.jsonl`, `metrics.json`, and `handoff-test/`.
Quality uses the frozen local evaluation: best valid validation Dice, final selected
Dice, and a structurally valid `filament_id,segmentation_rle` submission. An optional
leaderboard score is recorded only after explicit submission approval.

Efficiency reports active seconds, tokens, estimated cost, turns, tool calls,
repeated reads, failed commands, retries, debug cycles, and human interventions.
Decision/provenance, hidden-question retrieval, handoff recovery/continuation, and
immediate human usability retain raw component scores. A composite never suppresses
raw regressions.

## Marginal comparisons

Report each singleton minus baseline; `memory-seed-{x}` minus `memory-seed`; and
`memory-seed-{x}` minus `{x}`. Pilot deltas are diagnostic only.

## Failure and rerun rules

Substantive failures remain outcomes. Provider outage, invalid infrastructure,
Colab interruption, CUDA allocation failure, or the six-hour/20-minute watchdog is
a harness failure and may be rerun with the original run id plus an incremented
attempt. Resumption must use the recorded checkpoint. Credential leakage, parent
runtime writes, data/hash mismatch, hidden-question leakage, undeclared tools, or
an unrecorded methodology change invalidates the run.

## Human gates

The owner must accept Kaggle's rules and approve the completed freeze manifest.
Live Kaggle submission, paid compute purchase, release, or publication requires a
separate live instruction.
