# Frozen evaluation contract

The benchmark owner supplies one immutable validation manifest after inspecting the
official data. It assigns every training image to exactly one of `train` or
`validation`, records the generation seed/method, and is fingerprinted by
`benchmark.json`. Subjects may not edit it or tune on Kaggle's public leaderboard.

The starter repository must expose one command that evaluates a checkpoint against
that split and emits JSON containing at least `mean_dice`, per-image scores,
fragmentation count, over-segmentation count, evaluator version, checkpoint hash,
and validation-manifest hash. The same command validates the final RLE submission.
The harness records these outputs; it does not reimplement or silently approximate
the competition's custom evaluator.

Quality ordering is: highest valid `mean_dice`, then lower fragmentation, then lower
over-segmentation. Compute time is never a quality tiebreaker. If the official local
metric cannot be reproduced, the freeze remains blocked.

Leaderboard submission is optional and later. A public score is a reported field,
not a replacement for the frozen local result.
