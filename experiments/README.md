# Experiment inventory

This directory contains active instruments, frozen regression fixtures, and retained evidence. Age alone
does not make an experiment disposable: failed and superseded instruments often preserve the evidence for
why a later design changed.

Audit date: 2026-09-08

This is a family-level front door, not an exhaustive run ledger. Each experiment directory remains the
authority for its own preregistrations, fixtures, runs, and findings; session entries record the decisions
drawn from them.

| Directory | Status | Why it remains useful |
|---|---|---|
| `adr-campaign` | Reference | Source experiment for inverse ADR coverage; the supported ESR implementation still names its lineage analysis as provenance. |
| `agent-capture` | Retained evidence | Measures unprompted decision capture. The field-evidence report cites the current run matrix, while memory explicitly protects `runs-v1-json` and `runs-veto` as primary evidence. |
| `band-calibration` | Active reference | Holds the reproducible evidence behind current retrieval-band and lifecycle-guard findings. |
| `context-derivation` | Active input | Supplies frozen tasks, adversarial fixtures, Constitution-aware retrieval work, and prior misses reused by Task Packet calibration. Generated fixtures are regenerable. |
| `decision-replay` | Active and retained evidence | The version sequence records instrument failures, negative controls, and safety refinements through the current decision-edge work. The Codex v2 raw pilot remains unique evidence explicitly preserved for adjudication. |
| `decision-retrieval-scale` | Active reference | Supports the measured conclusion that the current relevance band is uncalibrated at corpus scale. |
| `memory-grounded-conclusions` | Regression fixture | Tests that an agent consults memory before recommending consequential removal. It is intentionally separate from capture-rate experiments. |
| `memory-index-dryrun` | Reference baseline | Original dry-run corpus and instrument used to compare later replication behavior. |
| `memory-index-dryrun-corpus2` | Active evidence | Independent replication and the recent orientation/reconciliation runs used by the current calibration roadmap. |
| `seed-pod-task-packet-evaluation` | Completed evaluation evidence | Records the clean-context Seed Pod packet evaluation that exposed authority-projection, path-scope, new-file, and execution-receipt gaps and led to the current Task Packet hardening plan. |
| `semantic-compression` | Deferred experiment | Negative and ceiling findings remain decision evidence; the confirmatory natural-authoring stage is not yet run. |
| `stack-benchmark` | Draft independent benchmark | A preregistered external context-stack benchmark. It is not part of Task Packet calibration, but retirement requires an owner decision because its design remains valid and referenced. |
| `task-packet-calibration` | Active | Current three-arm Memory Seed and compiled-packet calibration programme. |

## Cleanup rule

- Keep tracked definitions, preregistrations, frozen inputs, result summaries, and evidence explicitly
  retained by a decision or cited by a live plan.
- Keep ignored raw runs when they are the only evidence for a published finding or are explicitly named
  as retained evidence.
- Freely regenerate Python bytecode, temporary logs explicitly labelled noise, and generated fixture
  trees whose authoritative sources and fingerprints are tracked.
- Before deleting an experiment, search current references and Memory Seed history. Record a retirement
  decision when the experiment's evidence has a durable replacement; do not infer retirement from age,
  a failed result, or a newer version number.

## 2026-09-01 cleanup

Removed only regenerable residue: experiment-local `__pycache__` directories, the context-derivation
generated fixture tree, the band-calibration raw semantic log, and one ignored local Claude settings file.
No tracked experiment or retained raw evidence was removed.

## 2026-09-08 reconciliation

Reconciled this index against current `main`, added the Seed Pod Task Packet evaluation family, and
updated decision replay to reflect its continuing evidence work. No experiment files, fixtures, or results
were removed. Future additions to `experiments/` should update this front door in the same change when they
introduce a new experiment family.
