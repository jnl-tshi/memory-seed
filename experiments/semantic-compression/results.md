# Results

Stage 1 is complete; Stage 2 comprehension and fidelity evaluation is planned, not yet preregistered or run. These results cannot justify a production sidecar.

| Arm | Mean token proxy | Relative context | Recall@5 | MRR | Efficiency | Link F1 | Link FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw | 351.4 | 1.000 | 0.630 | 0.582 | 0.582 | 0.857 | 0.333 |
| core | 45.4 | 0.129 | 0.470 | 0.371 | 2.871 | 0.667 | 1.000 |
| core_why | 86.3 | 0.246 | 0.560 | 0.463 | 1.886 | 0.667 | 0.333 |
| core_why_constraint | 127.3 | 0.362 | 0.570 | 0.502 | 1.386 | 0.400 | 0.333 |
| labeled_spans | 133.7 | 0.380 | 0.570 | 0.502 | 1.320 | 0.400 | 0.333 |

See `metrics.json` for aggregate measurements and `relationship-pairs.json` for the exact labeled, split, scored relationship table and corpus identity.

## Interpretation

- `raw` achieved the best retrieval MRR (`0.582`).
- Core used 12.9% of raw representation-body context, with retrieval MRR `0.371` and Recall@5 `0.470`.
- Core + why + constraint used 36.2% of raw context and MRR `0.502`; this is a measurable tradeoff, not non-inferiority.
- The labeled-span diagnostic used 38.0% of raw context and MRR `0.502`. It tests whether labels alter this extractive span selection; it is not a rich-semantic upper bound.
- 14 fully scoped positive decision edges yielded 6 test pairs. The relationship task is underpowered and inconclusive. It is also a synthetic known-edge-versus-unlabeled diagnostic: unlabeled candidates may be real but unauthored relationships, so apparent precision/FPR are not semantic truth.

The efficiency composite rises as text shrinks, but that arithmetic does not erase absolute quality losses. Stage 1 therefore provides no evidence that compression improves retrieval; relationship detection is inconclusive. It establishes a measurable context/quality tradeoff for a future Stage 2 to test on actual comprehension and fidelity.
