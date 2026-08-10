# Recommendation

## INVESTIGATE FURTHER

Stage 1 establishes the compression/retrieval/link-discrimination frontier for extractive
representations. It does not measure whether an agent correctly understands the decision or whether
a generated compression silently changes modality, certainty, scope, causality, or terminology.

Therefore none of `BUILD`, `BUILD MINIMAL VERSION`, or `DO NOT BUILD` is yet supported. The next
decision gate is a planned blinded Stage 2 comprehension and semantic-fidelity evaluation; it is not yet
preregistered because its executable protocol and materials have not been frozen.
If a compact arm does not pass the fidelity gate, it is rejected regardless of token efficiency.
If it passes but does not materially improve performance per context, the recommendation becomes
`DO NOT BUILD`. Only the smallest arm on the measured Pareto frontier can become a build candidate.

Current evidence does not support labels alone: raw wins the adequately sized retrieval task, the
decision-edge task is underpowered, and the labeled-span diagnostic adds context over
`core + why + constraint` without improving retrieval. If Stage 2 is funded, prioritize `raw`,
`core + why`, and `core + why + constraint`; retain `labeled_spans` only as a planned label-format
comparator.
