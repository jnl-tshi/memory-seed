# Conversation-window strategy ablation

## Question

How much retained Codex conversation can be removed while preserving the manually cited source turns for the frozen 50-decision gold cohort?

## Strategies

- **Fixed radius 2:** the existing winning turn plus two turns on either side.
- **Backward 5:** fixed window plus five causal turns before the decision-time anchor, including continuations of the same logical task.
- **Backward 12:** the same unconditional span with a 12-turn lookback.
- **Plan adaptive 12:** fixed window plus the span back to the nearest Plan-mode turn within 12 causal turns; if none exists, fall back to five turns.
- **Plan + lineage adaptive 12:** Plan-adaptive expansion plus the same bounded search in parent tasks, with each parent cut off at child creation time.
- **Lineage + backward 12:** unconditional 12-turn expansion in the selected task and traversed parents; this is the high-recall control for the Plan-mode heuristic.
- **Lineage + backward 20:** the proposed wider safety envelope: up to 20 preceding turns plus the anchor in each selected/parent task, using the same causal and lineage rules. The fixed-radius union can add turns.

All strategies are structural and were applied without reading gold evidence coordinates. Gold coordinates are used only for scoring. Encrypted reasoning and raw chat text are not written to the outputs.

## Results

| Strategy | Any cited evidence | All cited evidence | All evidence, verified 42 | Mean turns retained | Reduction vs search universe | Reduction vs source task/lineage |
|---|---:|---:|---:|---:|---:|---:|
| fixed radius 2 | 19/20 (95.0%) | 18/20 (90.0%) | 14/16 (87.5%) | 4.2 | 97.1% | 90.8% |
| backward 5 | 19/20 (95.0%) | 18/20 (90.0%) | 14/16 (87.5%) | 5.9 | 95.9% | 87.1% |
| backward 12 | 19/20 (95.0%) | 18/20 (90.0%) | 14/16 (87.5%) | 8.7 | 94.0% | 81.1% |
| plan adaptive 12 | 19/20 (95.0%) | 18/20 (90.0%) | 14/16 (87.5%) | 6.0 | 95.9% | 87.0% |
| plan lineage adaptive 12 | 19/20 (95.0%) | 20/20 (100.0%) | 16/16 (100.0%) | 7.2 | 95.0% | 84.4% |
| lineage backward 12 | 19/20 (95.0%) | 20/20 (100.0%) | 16/16 (100.0%) | 11.2 | 92.2% | 75.5% |
| lineage backward 20 | 19/20 (95.0%) | 20/20 (100.0%) | 16/16 (100.0%) | 14.8 | 89.8% | 67.8% |

`Any cited evidence` is candidate-region recall. `All cited evidence` is the stricter window-completeness measure. Neither metric converts partial or child-result rows into verified decisions.

## Finding

`plan_lineage_adaptive_12` is the smallest tested strategy meeting the exploratory 98% target on complete cited evidence for verified decisions (16/16).

Across all 50 adjudicated rows, including partial and child-result cases, `plan_lineage_adaptive_12` is strongest: 20/20 contain every cited source turn and all 20 contain at least one, while removing 95.0% of the temporal search universe. Compared with the 12-turn version, the extra recovered case is partial rather than a verified source.

Plan-mode anchoring did not improve cited-evidence recall over the five-turn fallback (18/20 versus 18/20). Plan mode remains a useful ranking signal, but the nearest Plan turn is not a safe stopping boundary for high-recall context expansion.

The search-universe denominator is the per-decision set of repository turns eligible under the existing 72-hour temporal rule. The source denominator is the causally prior selected logical task plus traversable parent lineage. Counts are micro-averaged across 50 decision retrieval instances, so a turn may count once for each decision that could have retrieved it.

## Limits

- The same 50 rows were used to motivate and evaluate these structural variants; a held-out cohort is required before treating the best setting as stable.
- Gold evidence marks the manually cited source turns, not every possibly useful context turn.
- Turn-count reduction does not model token length; long and short turns have equal weight.
- The cohort has 42 strict positives and no reviewed negatives, so this remains a retrieval experiment rather than classifier training evidence.

## Reproducibility

- Gold rows: 20
- Gold sample hash: `e1fb0f77272bed5f17c11c11203ef330fa29fba6c718dc6062d7f97168b96dfb`
- Parsed repository rollouts: 943
- Parsed turn blocks: 4499
- Plan lookback cap: 12 turns
- Safety lookback: 20 turns
- Fallback lookback: 5 turns
- Parent depth cap: 2
