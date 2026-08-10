# Recommendation

## INVESTIGATE FURTHER

Stage 1 establishes the compression/retrieval/link-discrimination frontier for extractive
representations. The follow-on lean-DRAFT feasibility pilot adds independent semantic/identifier
queries and an arm-label-hidden, source-grounded, same-model structured audit. It does not replace a
natural-authoring study or human comprehension and delayed-recall evaluation.

The pilot rejects one tempting implementation now: **do not shorten canonical DRAFT decisions to a
mechanically selected decision+rationale+boundary card**. The card used 44.1% of raw decision-block
context, but semantic MRR fell by 0.118 and adjudicated critical fidelity errors occurred on 50% of
cards versus 0% raw. Slightly higher clarity cannot compensate for lost action, scope, modality, and
adoption-status boundaries.

Supplemental exact identifiers improved identifier-query MRR by 0.069, but the 95% interval crossed
zero and a six-anchor selector preserved only 86.9% of source anchors under identifier-boundary
matching. Preserve exact terminology in
future previews, but do not claim this selector is validated.

Therefore none of `BUILD`, `BUILD MINIMAL VERSION`, or `DO NOT BUILD` for a production meaning layer
is yet supported. The next decision gate is a planned blinded Stage 2 natural-authoring, comprehension,
semantic-fidelity, and delayed-recall evaluation; it is not yet preregistered because its executable
protocol and materials have not been frozen.
If a compact arm does not pass the fidelity gate, it is rejected regardless of token efficiency.
If it passes but does not materially improve performance per context, the recommendation becomes
`DO NOT BUILD`. Only the smallest arm on the measured Pareto frontier can become a build candidate.

Current evidence does not support labels alone: raw wins the adequately sized retrieval task, the
decision-edge task is underpowered, and the labeled-span diagnostic adds context over
`core + why + constraint` without improving retrieval. If Stage 2 is funded, prioritize `raw`,
`core + why`, and `core + why + constraint`; retain `labeled_spans` only as a planned label-format
comparator.

For draft usability, the present recommendation is narrower and actionable: keep full prose canonical
and do not ship the measured compact selector. Progressive disclosure with a safer selector, source ref,
and full decision one action away is a future UI/retrieval hypothesis that still requires evaluation,
not a current implementation recommendation or write-format change.
