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
The task manifest, gold labels, preregistration, frozen candidate,
`OFFLINE_SELECTION.json`, `PROBE_PINS.json`, `LIVE_MATRIX.json`, summary, and
final report are the durable experiment artifacts. Live execution revalidates
their fingerprints and the current resolver source before any subject call.

No scored stage may start until `PREREGISTRATION.md` and `tasks/gold.json` have
been approved by the repository owner. Calibration and unit tests are unscored.

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

6. Run exactly two unscored observations per provider outside the repository,
   then update and commit `LIVE_MATRIX.json` with status `FROZEN`, exact
   model/CLI pins, candidate fingerprint, and v1 fingerprint. Codex requires a
   canonical slug from its bundled model catalog; Claude records the canonical
   model reported by its transcript. Probe artifacts never enter scored `runs/`:

   ```text
   python experiments/context-derivation/probe.py --owner-approved --agent claude --model <model> --cli-version <version> --output <os-temp-path>
   python experiments/context-derivation/probe.py --owner-approved --agent codex --model <canonical-model-slug> --cli-version <version> --effort <effort> --output <os-temp-path>
   ```

   The committed `JUDGE_SELECTION.json` already freezes all 96 secondary-review
   cells before results exist.
7. Dry-run the exact 288-cell schedule, then launch only with the explicit flag:

   ```text
   python experiments/context-derivation/batch.py --dry-run --claude-model <model> --codex-model <model> --codex-effort <effort> --claude-cli-version <version> --codex-cli-version <version>
   python experiments/context-derivation/batch.py --owner-approved --claude-model <model> --codex-model <model> --codex-effort <effort> --claude-cli-version <version> --codex-cli-version <version>
   ```

   The scored batch fails before creating `runs/` or contacting either provider
   until `codex_interactive_ready()` confirms an owner-approved privilege broker.
   Fixed-arm cells cannot run early and leave a partial scored matrix.

8. Collect, score, run the frozen blind reviews, and render the report. Scoring
   and judge execution also verify the frozen live artifacts. The report accepts
   the offline reduction, all 96 judgements, and a reviewed recommendation JSON;
   it never authorizes a production change itself.

Subject processes execute in OS-temporary directories outside the repository.
Fixed packet arms have no MCP tools and no fixture copy. Interactive fixtures are
immutable, regular-file-only copies outside the subject workspace. Claude reaches
its copy through the narrow stdio facade with built-in filesystem, shell, web, and
task tools disabled. The provider-free Codex broker binds a kernel-assigned
`127.0.0.1` port, requires a fresh per-run bearer token supplied only through the
subject environment, advertises the exact arm allowlist, forces every tool `cwd`
to its isolated fixture, validates ADR IDs against traversal, redacts host paths,
forces deterministic lexical search, and drains active handlers before verified
teardown. Codex keeps the deny-read, no-network, no-shell, no-web, no-apps
permission profile.

The scored Codex path remains deliberately disconnected from the broker and
`codex_interactive_ready()` remains false. Building and locally validating the
approved trust boundary therefore cannot start either a single provider subject
or the 288-run matrix. Connecting that final path requires a separate live
execution approval. Parent and fixture fingerprints, undeclared tools, direct
filesystem retrieval, model/CLI pins, answer schemas, and redacted retained
provider artifacts are rechecked during collection and scoring.
