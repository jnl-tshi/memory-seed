# Lean DRAFT feasibility pilot

This is a derived decision-block pilot, not a natural-authoring study and not a change to the DRAFT grammar.

| Arm | Mean token proxy | Relative context | Semantic R@5 | Semantic MRR | Anchor R@5 | Anchor MRR |
|---|---:|---:|---:|---:|---:|---:|
| raw | 351.4 | 1.000 | 0.600 | 0.520 | 0.867 | 0.818 |
| decision_only | 46.7 | 0.133 | 0.133 | 0.110 | 0.667 | 0.620 |
| lean_no_supplemental_anchors | 131.7 | 0.375 | 0.567 | 0.404 | 0.800 | 0.695 |
| lean_front_door | 155.0 | 0.441 | 0.567 | 0.403 | 0.833 | 0.764 |

| Arm | Model-rated clarity /5 | Model-rated findability /5 | Decision complete | Rationale complete | Boundary complete | Adjudicated critical error |
|---|---:|---:|---:|---:|---:|---:|
| raw | 3.40 | 5.00 | 100.0% | 100.0% | 100.0% | 0.0% |
| decision_only | 4.18 | 3.72 | 41.7% | 0.0% | 28.3% | 70.0% |
| lean_no_supplemental_anchors | 3.78 | 4.08 | 63.3% | 53.3% | 51.7% | 50.0% |
| lean_front_door | 3.73 | 3.95 | 63.3% | 53.3% | 51.7% | 50.0% |

## Interpretation

- The lean card uses 44.1% of raw decision-block context; decision-only uses 13.3%.
- On independently worded semantic queries, lean MRR is 0.403 versus raw 0.520 and decision-only 0.110.
- Lean minus raw semantic MRR is -0.118 (decision-bootstrap 95% CI -0.267 to +0.024), failing the provisional -0.05 margin.
- On identifier queries, supplemental exact anchors change MRR from 0.695 to 0.764; the paired effect is +0.069 (95% CI -0.018 to +0.162), so this pilot does not establish a non-zero benefit.
- The strict anchor gate also missed: semantic MRR changed from 0.404 without supplemental anchors to 0.403 with them, rather than remaining non-decreasing.
- Every compact clause and identifier is extractive. That establishes source grounding, not full semantic completeness.
- An arm-label-hidden, same-model structured audit (two ratings per card across four reviewer processes) plus adjudication flagged a critical loss on 50.0% of lean cards versus 0.0% raw; pooled raw agreement was 96.7%. Candidate form and exact source matching made the raw arm recognizable, so this is not confirmatory reader evidence.
- Model-rated lean clarity was slightly higher (3.73 vs 3.40), but its findability was lower (3.95 vs 5.00); these ratings cannot offset the fidelity failure.
- Outcome: the theory is not validated for shortening canonical drafts, and the measured selector should not ship. Progressive disclosure with a safer selector and immediate full-source access is the next hypothesis worth testing; exact identifiers are a candidate field, not a validated feature.
- A confirmatory authoring study still needs independently authored paired records, human readers, and delayed recall before changing guidance.
