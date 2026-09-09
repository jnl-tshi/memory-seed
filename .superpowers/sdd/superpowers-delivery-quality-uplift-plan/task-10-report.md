# Task 10 — full behavioural evaluation report

## Summary

Expanded the existing local delivery-quality evaluator's declared scenario corpus; no second evaluator
or workflow controller was introduced. The corpus now has 12 positive synthetic instrument fixtures and
18 expected-failure controls. New structured, observable cases cover governed topic applicability,
optional implementation planning with a viable test/alternative-check strategy, and Reflection Board
reuse discovery. The existing corpus continues to cover consequential design discovery, systematic
debugging, fresh verification, constitutional authority conflict, scoped-evidence invalidation, routine
non-trigger routing, evidence-aware review, and the approved and fallback external-boundary routes.

Fixtures remain `fixture_instrument_validation` and cannot make a workflow claim. The bounded
Reflection Board overlap comparison remains the only real-work evidence: its baseline and post-adoption
records both passed local artifact binding, but they are not a causal delivery-uplift conclusion.

## Files changed

- `experiments/delivery-quality/scenarios.json` — three observable scenarios and six negative controls.
- `experiments/delivery-quality/README.md` — current corpus/provenance scope.
- `tests/test_delivery_quality.py` — corpus-coverage and structured negative-control assertions.
- `.superpowers/sdd/superpowers-delivery-quality-uplift-plan/task-10-report.md` — this report.

## Evaluation results

| Evidence set | Result | Provenance / claim boundary |
| --- | --- | --- |
| Valid fixtures | 12 passed, 0 failed | Synthetic instrument validation; all measurement fields unavailable; not workflow-claim eligible. |
| Negative controls | 18 expected failures, 0 unexpected passes | Includes absent observations, prohibited routing/actions, malformed/missing evidence, and the new topic, plan-strategy, and reuse controls. |
| Reflection Board baseline | passed | `real_agent_behavior`; bound `baseline-run.json` artifact digest verified. |
| Reflection Board post-adoption | passed | `real_agent_behavior`; bound `post-adoption-run.json` artifact digest verified. |

The comparison reports provider token usage, latency, and cost as `unavailable` because the delegated
execution reports exposed none of those measurements. No token estimate, local elapsed time, price
ceiling, or inferred cost was substituted.

## Exact commands and results

```text
python -m pytest tests/test_delivery_quality.py -q
17 passed in 0.41s

python experiments/delivery-quality/evaluate.py --fixture valid
12 passed, 0 failed

python experiments/delivery-quality/evaluate.py --fixture negative
18 expected failures, 0 unexpected passes

python experiments/delivery-quality/evaluate.py --input experiments/delivery-quality/runs/reflection-board-overlap/baseline-result.json
passed; provenance_verified=true; workflow_claim_eligible=true

python experiments/delivery-quality/evaluate.py --input experiments/delivery-quality/runs/reflection-board-overlap/post-adoption-result.json
passed; provenance_verified=true; workflow_claim_eligible=true

git diff --check
no output (passed)
```

## Evidence provenance and limitations

- The 12 fixture results exercise only the offline scorer. Their structured evidence records are
  intentionally synthetic and must never be reported as actual workflow runs.
- The two real-run inputs are reconstructed from delegated terminal reports and locally bound to their
  stored JSON artifacts. Binding verifies the scorer consumed the claimed record; it does not authenticate
  the external provider or establish first-hand collection.
- The Reflection Board comparison is a single selected, read-only advisory overlap case. It was not random,
  was not an implementation comparison, and cannot establish causal quality, rework, speed, token, latency,
  cost, or delivery uplift.
- The post-adoption run could not verify the active-client upstream version and observed that the Board CLI
  did not return within 30 seconds. Board reactivation remains deferred to a bounded reversible trial.

## Commit and scope statement

Implementation commit: `dea203f7` (`test: complete delivery quality scenario corpus`).

No files outside the Task 10 allow-list changed.
