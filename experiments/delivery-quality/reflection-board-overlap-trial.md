# Reflection Board overlap comparison

## Method

This bounded comparison packages two delegated terminal reports for the same `new-consequential-design`
scenario: whether to keep the Memory Seed Reflection Board dormant and rely on Superpowers SDD for
overlapping execution/review, or retain both. Both runs used the same model tier and clean HEAD
`e3e6d233e586a83a34c35e2b4e6e105f2e8a1d88`. The baseline was explicitly denied the new design-discovery,
systematic-debugging, planning-policy, and evaluation files. The post-adoption run applied the new
design-discovery and governed-planning contracts. Records are reconstructed from the delegated agents'
terminal reports; the local artifact binding proves packaging integrity, not provider authenticity or
first-hand capture.

## Comparable controls

Both result inputs use the same declared scenario, task complexity (`medium`), required discovery
observations, and unavailable provider measurements. They have distinct run and execution-surface IDs,
separate SHA-256-bound execution artifacts, and explicitly record selection bias, limitations, and
reconsideration events. No Reflection artifacts were changed and the post-adoption run was advisory and
read-only rather than an implementation.

## Evaluator results

- Baseline: `python experiments/delivery-quality/evaluate.py --input baseline-result.json` — passed;
  `real_agent_behavior`, provenance verified, workflow-claim eligible.
- Post-adoption: `python experiments/delivery-quality/evaluate.py --input post-adoption-result.json` —
  passed; `real_agent_behavior`, provenance verified, workflow-claim eligible.

The result inputs and execution artifacts are in
`experiments/delivery-quality/runs/reflection-board-overlap/`.

## Observed difference

Both runs inspected existing capabilities, compared realistic alternatives, and recorded the same
decision: retain Reflection code/history/read-only integrity, keep writes dormant, use verified SDD for
eligible approved same-session multi-task work, and reconsider Board reactivation only through a bounded
trial demonstrating a unique coordination gap. The post-adoption record additionally reports
consultation of the Constitution, accepted ADR heads, active decision evidence, governed policy/config,
and definition of a two-plan reversible trial.

## Limitations and conclusion

This is one selected overlap case, and the baseline and post-adoption records are reconstructed rather
than first-hand captures. The baseline reported an ambiguous-history malformed Board candidate; the
post-adoption report was read-only, could not verify the active-client upstream version, and observed a
Board CLI timeout after 30 seconds. Provider token usage, latency, and cost were unavailable for both;
they are not inferred from estimates or local timing. The sample demonstrates that the new route can
preserve the chosen decision while adding richer authority/trial structure. It does not establish causal
uplift, speed, token, latency, cost, quality, or general workflow improvement.
