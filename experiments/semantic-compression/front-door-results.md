# Front-door development diagnostic

This reuses the earlier source-conditioned development set. Ranking evaluates raw decision bodies; display arms never enter the ranker and this is not human-comprehension evidence.

| Retrieval arm | Semantic MRR | Identifier MRR |
|---|---:|---:|
| body_only | 0.520 | 0.818 |
| current_lexical_terms | 0.520 | 0.818 |
| authored_exact_terms | 0.520 | 0.818 |
| union_terms | 0.520 | 0.818 |

| Display arm | Mean displayed bytes | Mean raw-context ratio | Fallback rate |
|---|---:|---:|---:|
| raw | 1358.8 | 1.000 | 0.0% |
| current_lean | 679.8 | 0.500 | 0.0% |
| complete_dra | 1071.1 | 0.788 | 6.7% |
| query_evidence | 1119.9 | 0.824 | 6.7% |

The `Full source: <decision_ref>` affordance is included in every non-raw display size. All displayed D/R/A source blocks are checked mechanically for exact projection integrity.

## Gate observations

- Union identifier terms versus body-only identifier MRR: +0.000 (95% CI +0.000 to +0.000).
- Union identifier terms versus the current lexical-term field: +0.000 (95% CI +0.000 to +0.000).
- Union semantic MRR versus body-only: +0.000 (95% CI +0.000 to +0.000).
- Query-evidence display retains 97.8% of source-only answer spans and all required spans on 96.7% of queries.
- Query-evidence median first-view context, including the full-source affordance, is 86.2% of raw.
- These are development-set retrieval and evidence-disclosure measurements, not human comprehension, writing-quality, or delayed-recall results.
