# P0.2 offline evaluation

Status: **feasibility finding; do not promote to production**.

The frozen manifest contains 103 formal source-labelled records: 100 typed Decisions and three Documentation
controls. The permitted partitions are 80 development decisions, 15 clean descriptive held-out decisions, and
13 audit-only controls/contaminated rows/post-audit amendments. The canonical corpus SHA-256 is
`86566e4d68482ce10b8cc1441e795bf5b2c9df84462c0120c09b795ee8ebf46c`; the manifest SHA-256 is
`bc5757d00e6dff2aef037b8b6e4fb6fd9d2bed1c560e58ea0652752980535c2f`.

Measured results from the owner-local offline replay:

| Gate | Result | Threshold | Outcome |
| --- | ---: | ---: | --- |
| valid marker recovery | 30 / 30 | 100% | pass |
| deterministic parser output | byte-identical across 3 runs | identical | pass |
| marker-assisted source-window recall | 89.6% (60 / 67) | at least 95% | **fail** |
| unmarked historical source-window recall | 80.6% (54 / 67) | at least 80% | pass |
| accepted vs proposal-only precision | 100% on 8 synthetic controls | at least 90% | pass |
| replay duplication | none | none | pass |
| paused-period implicit backfill | none | none | pass |
| p95 local capture latency | 23.64 ms | below 30 s | pass |

The failed marker-assisted result is not hidden or tuned away. Seven verified gold cases span more turns than the
approved current-turn/two-prior/one-following region. The bounded region therefore cannot contain every cited
coordinate even with a perfect marker. P0.2 establishes a functioning local capture path, but not the agreed
marker-assisted recall threshold.

Residual risks:

- Codex rollout files are undocumented local storage; the allowlist is intentionally narrow and will require
  explicit validation for each new client/schema version.
- The gold corpus is retrospective and decision-known. Only 15 held-out rows are source-lineage-clean, and only
  14 of those are verified recall denominators.
- Accepted/proposed is not labelled in the historical corpus, so accepted-state precision is measured only on
  synthetic negative controls.
- The pinned `spaCy 3.8.16` / `en_core_web_sm 3.8.0` backend was validated from an isolated temporary
  dependency directory. It remains intentionally absent from the OSS package and must be provisioned separately.
- No draft is authoritative. Curator evidence, attribution, and atomicity checks remain mandatory.

Machine-readable results are in `results/evaluation.json`, with canonical corpus rows and hashes beside it.
