# Semantic Compression Benchmark

Status: Stage 1 measured; Stage 2 not yet run.

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
100 stratified decisions from frozen revision `54de83ca7f3e279f1199b721e6aa1bec825e04ac`. Stage 2 is
planned but not yet preregistered: its executable materials remain to be frozen. A build recommendation
is prohibited until Stage 2 is complete.

Run:

```powershell
python experiments/semantic-compression/benchmark.py
```

Outputs are isolated in this directory. `dataset.json`, `metrics.json`, `relationship-pairs.json`, and
`results.md` are regenerable from the fixed source revision; the recorded corpus fingerprint prevents a
new session entry from silently changing the measurement.
