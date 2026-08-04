# ADR context-derivation experiment

This directory contains the pre-registered, read-only benchmark for deriving
minimal but sufficient ADR, decision, and lifecycle-link context. It does not
change Memory Seed's production retrieval or MCP contracts.

## Stages

1. `generate_fixtures.py` creates isolated real and adversarial runtimes.
2. `sweep.py` evaluates deterministic context strategies in parallel.
3. `reduce.py` applies the hard gates and freezes one Pareto candidate.
4. `batch.py` schedules the 288 Claude/Codex subject runs.
5. `collect.py`, `score.py`, `judge.py`, and `report.py` produce separate
   per-agent results and the recommendation packet.

Generated fixtures, packs, shards, raw runs, and judgements are gitignored.
The task manifest, gold labels, preregistration, frozen candidate, summary, and
final report are the durable experiment artifacts.

No scored stage may start until `PREREGISTRATION.md` and `tasks/gold.json` have
been approved by the repository owner. Calibration and unit tests are unscored.
