# Identifier-lane held-out diagnostic

This target/query set is disjoint from the development set that exposed the normalization defect.
The ranker and BM25F weight are unchanged; only lexical-field representation differs.

| Arm | Semantic MRR | Identifier MRR | Identifier R@5 | Full-order changes |
|---|---:|---:|---:|---:|
| body_only | 0.957 | 1.000 | 1.000 | 0 |
| current_lexical_terms | 0.957 | 1.000 | 1.000 | 0 |
| normalized_current_terms | 0.957 | 1.000 | 1.000 | 12 |
| normalized_authored_terms | 0.957 | 1.000 | 1.000 | 14 |
| normalized_union_terms | 0.957 | 1.000 | 1.000 | 18 |

## Paired effects

- `normalized_current_terms` vs `body_only` identifier MRR: +0.000 (95% CI +0.000 to +0.000; 0 improved, 0 regressed).
- `normalized_current_terms` vs `current_lexical_terms` identifier MRR: +0.000 (95% CI +0.000 to +0.000; 0 improved, 0 regressed).
  Decision: **no-improvement**.
- `normalized_authored_terms` vs `body_only` identifier MRR: +0.000 (95% CI +0.000 to +0.000; 0 improved, 0 regressed).
- `normalized_authored_terms` vs `current_lexical_terms` identifier MRR: +0.000 (95% CI +0.000 to +0.000; 0 improved, 0 regressed).
  Decision: **no-improvement**.
- `normalized_union_terms` vs `body_only` identifier MRR: +0.000 (95% CI +0.000 to +0.000; 0 improved, 0 regressed).
- `normalized_union_terms` vs `current_lexical_terms` identifier MRR: +0.000 (95% CI +0.000 to +0.000; 0 improved, 0 regressed).
  Decision: **no-improvement**.

Sensitivity control passed: **True**.
A positive point estimate whose interval crosses zero is promising, not validated.
This diagnostic does not authorize a production retrieval change by itself.
