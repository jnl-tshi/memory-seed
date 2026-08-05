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

## Draft strong-context supplement

`strong_context_fixture_v2.py` joins a generated fixture's parsed ADR ledgers,
explicit Constitution blocks, and the production decision-level ranking reader
in memory only. `strong_context_sweep_v2.py` compares bounded high-signal
allocations in parallel; its top-K output is an offline diagnostic, never an
MCP field. See `STRONG_CONTEXT_V2_NOTES.md` for the proposed revision-scoped
Constitution binding to evaluate. These files cannot select a candidate or
authorize scored/offline-agent execution until versioned Constitution-aware
task and gold definitions receive review.

## Freeze and execution sequence

The gates are intentionally split. Before approval, only definition checks,
fixture determinism, unit tests, schedule dry-runs, and label-free smoke sweeps
are allowed. `reduce.py` is the first gold-aware stage and refuses to run until
both owner-review markers are approved.

1. Review `PREREGISTRATION.md`, `tasks/manifest.json`, and `tasks/gold.json`.
   Approval is a separate commit changing the preregistration status and gold
   `approval_status` to `APPROVED`.
2. Build isolated fixtures and the normalized strategy manifest:

   ```text
   python experiments/context-derivation/generate_fixtures.py
   python experiments/context-derivation/strategies.py --output experiments/context-derivation/generated/strategies.json
   ```

3. Run the label-free sweep. The grid is a bounded factorial plus explicit
   pairwise state and budget probes; equivalent normalized fingerprints are
   removed before scheduling.

   ```text
   python experiments/context-derivation/sweep.py --tasks experiments/context-derivation/generated/tasks.json --strategies experiments/context-derivation/generated/strategies.json --fixture-base experiments/context-derivation --output experiments/context-derivation/shards
   ```

4. After owner approval, apply hard gold gates and exclusively create the
   candidate manifest:

   ```text
   python experiments/context-derivation/reduce.py --owner-approved --shards experiments/context-derivation/shards --gold experiments/context-derivation/tasks/gold.json --strategies experiments/context-derivation/generated/strategies.json --freeze-candidate experiments/context-derivation/FROZEN_CANDIDATE.json --output experiments/context-derivation/generated/reduction.json
   ```

5. Materialize all twelve fixed-arm packets using the selected candidate and
   the predeclared current Retrieval Spec v1 fingerprint:

   ```text
   python experiments/context-derivation/materialize.py --tasks experiments/context-derivation/generated/tasks.json --shards experiments/context-derivation/shards --fixture-base experiments/context-derivation --candidate-manifest experiments/context-derivation/FROZEN_CANDIDATE.json --reduction experiments/context-derivation/generated/reduction.json --retrieval-fingerprint <frozen-v1-fingerprint> --output experiments/context-derivation/generated/live-tasks.json
   ```

6. Run unscored Claude/Codex probes, then update and commit `LIVE_MATRIX.json`
   with status `FROZEN`, exact model/CLI pins, candidate fingerprint, and v1
   fingerprint. The committed `JUDGE_SELECTION.json` already freezes all 96
   secondary-review cells before results exist.
7. Dry-run the exact 288-cell schedule, then launch only with the explicit flag:

   ```text
   python experiments/context-derivation/batch.py --dry-run --claude-model <model> --codex-model <model> --claude-cli-version <version> --codex-cli-version <version>
   python experiments/context-derivation/batch.py --owner-approved --claude-model <model> --codex-model <model> --claude-cli-version <version> --codex-cli-version <version>
   ```

8. Collect, score, run the frozen blind reviews, and render the report. Scoring
   and judge execution also verify the frozen live artifacts. The report accepts
   the offline reduction, all 96 judgements, and a reviewed recommendation JSON;
   it never authorizes a production change itself.

Subject processes execute in OS-temporary directories outside the repository.
Fixed packet arms have no MCP tools and no fixture copy. Interactive arms receive
one immutable fixture copy and an experiment-local MCP allowlist. Parent and
fixture fingerprints, undeclared tools, direct filesystem retrieval, model/CLI
pins, and answer schemas are rechecked during collection and scoring.
