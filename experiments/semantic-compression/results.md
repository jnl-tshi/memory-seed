# Results

Stage 1 is complete; Stage 2 comprehension and fidelity evaluation has not run. These results cannot justify a production sidecar.

| Arm | Mean token proxy | Relative context | Recall@5 | MRR | Efficiency | Link F1 | Link FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw | 351.4 | 1.000 | 0.630 | 0.582 | 0.582 | 0.857 | 0.333 |
| core | 45.4 | 0.129 | 0.470 | 0.371 | 2.871 | 0.667 | 1.000 |
| core_why | 86.3 | 0.246 | 0.560 | 0.463 | 1.886 | 0.667 | 0.333 |
| core_why_constraint | 137.4 | 0.391 | 0.580 | 0.508 | 1.298 | 0.667 | 0.333 |
| structured | 144.4 | 0.411 | 0.580 | 0.508 | 1.235 | 0.667 | 0.333 |

See `metrics.json` for raw counts, thresholds, confusion matrices, and fingerprints.

## Interpretation

- Raw achieved the best retrieval MRR (`0.582`).
- Core used 12.9% of raw representation-body context, but retrieval MRR fell to `0.371` and
  Recall@5 to `0.470`.
- Core + why + constraint is the most plausible compact frontier point in Stage 1: 39.1% of raw
  context and MRR `0.508`. That remains a material loss from raw, not
  non-inferiority.
- Structured semantics used more context than core + why + constraint and did not improve its
  Recall@5, nDCG@5, or relationship confusion matrix. Labels alone earned nothing in this arm.
- Only 14 fully scoped positive decision edges exist in this sample, leaving six test pairs. The
  relationship task is underpowered and inconclusive. It is also a synthetic
  known-edge-versus-unlabeled diagnostic: unlabeled candidates may be real but unauthored
  relationships, so apparent precision/FPR are not semantic truth.

The efficiency composite rises as text shrinks, but that arithmetic does not erase absolute quality
losses. Stage 1 therefore provides no evidence that compression improves retrieval; relationship
detection is inconclusive. It establishes a measurable context/quality tradeoff for Stage 2 to test on actual
comprehension and fidelity.
