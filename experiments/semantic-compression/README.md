# Semantic Compression Benchmark

Status: Stage 1, lean-DRAFT, front-door, and identifier-normalization diagnostics measured;
confirmatory natural-authoring Stage 2 not yet run.

This experiment asks whether a derived representation of a Memory Seed decision can preserve or
improve downstream utility while consuming less context. It does **not** add a production sidecar,
change the canonical session format, or authorize a semantic ontology.

The ablation arms are:

- `raw`: the complete decision chunk.
- `core`: the first source sentence under `D:`.
- `core_why`: `core` plus the first source sentence under `R:`.
- `core_why_constraint`: the preceding fields plus source sentences containing explicit modality
  or scope markers (`must`, `only`, `without`, `require`, and similar terms).
- `labeled_spans`: the same source-grounded spans prefixed with `claim`, `because`, and `constraint`
  labels. This is a label-format diagnostic, not a semantic upper bound or proposed schema.

Stage 1 measures deterministic compression, lexical retrieval, and synthetic known-edge versus
sampled-unlabeled discrimination over
100 stratified decisions from frozen revision `54de83ca7f3e279f1199b721e6aa1bec825e04ac`.

The separate [lean-DRAFT pilot](lean-draft-results.md) tests a practical follow-up: first decision,
rationale, accepted boundaries, and supplemental exact identifiers. It uses 60 independently worded,
source-only queries and an arm-label-hidden, same-model structured audit with two ratings per card.
The card cut decision-block context to 44.1%, but failed semantic-MRR and fidelity gates; it is not
safe as a canonical replacement, and the measured selector should not ship as a preview. Exact
identifiers showed a positive but inconclusive retrieval effect. Progressive disclosure with a safer
selector and immediate full-source access is only the next hypothesis to test.

The subsequent [front-door result](front-door-results.md) rejected the tested presentation candidate:
query-specific evidence added context without adding answer evidence, and the safer verbatim D/R/A view
missed its preregistered 20% median reduction gate. The fresh
[identifier-lane holdout](identifier-lane-results.md) then tested the minimal BM25F normalization repair.
The treatment was active and changed 12-18 full rankings, but complete raw-body retrieval already achieved
perfect exact-identifier MRR (`1.000`), so every normalized arm produced zero target-rank improvement. See
the [score audit](identifier-lane-audit.md) for the ceiling-effect and instrument checks.

Stage 2 is planned but not yet preregistered: its executable materials remain to be frozen. A
production build recommendation is prohibited until Stage 2 is complete.

Run:

```powershell
python experiments/semantic-compression/benchmark.py
python experiments/semantic-compression/lean_draft_pilot.py validate-queries
python experiments/semantic-compression/lean_draft_pilot.py run
python experiments/semantic-compression/identifier_lane_ablation.py validate-frozen-inputs
python experiments/semantic-compression/identifier_lane_ablation.py run --output-dir <new-directory>
```

Outputs are isolated in this directory. `dataset.json`, `metrics.json`, `relationship-pairs.json`, and
`results.md` are regenerable from the fixed source revision; the recorded corpus fingerprint prevents a
new session entry from silently changing the measurement.

`lean_draft_pilot.py` checks the corpus, current selector, query, reviewer, and adjudication hashes
before scoring. The selector hash is a post-first-run reproducibility lock, not evidence that the
selector was independently preregistered before outcomes. On OneDrive,
pass `--output-dir` to a writable temporary directory if the provider blocks generated-file writes;
the committed `lean-draft-metrics.json` and `lean-draft-results.md` are byte-stable LF outputs.
