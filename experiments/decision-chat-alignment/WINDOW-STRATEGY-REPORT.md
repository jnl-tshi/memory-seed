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

All strategies are structural and were applied without reading gold evidence coordinates. Gold coordinates are used only for scoring. Encrypted reasoning and raw chat text are not written to the outputs.

## Results

| Strategy | Any cited evidence | All cited evidence | All evidence, verified 42 | Mean turns retained | Reduction vs search universe | Reduction vs source task/lineage |
|---|---:|---:|---:|---:|---:|---:|
| fixed radius 2 | 50/50 (100.0%) | 42/50 (84.0%) | 39/42 (92.9%) | 4.7 | 97.5% | 88.8% |
| backward 5 | 50/50 (100.0%) | 43/50 (86.0%) | 40/42 (95.2%) | 7.0 | 96.2% | 83.2% |
| backward 12 | 50/50 (100.0%) | 46/50 (92.0%) | 42/42 (100.0%) | 12.0 | 93.5% | 71.1% |
| plan adaptive 12 | 50/50 (100.0%) | 43/50 (86.0%) | 40/42 (95.2%) | 7.0 | 96.2% | 83.0% |
| plan lineage adaptive 12 | 50/50 (100.0%) | 46/50 (92.0%) | 40/42 (95.2%) | 7.5 | 95.9% | 81.9% |
| lineage backward 12 | 50/50 (100.0%) | 49/50 (98.0%) | 42/42 (100.0%) | 12.9 | 93.0% | 68.9% |

`Any cited evidence` is candidate-region recall. `All cited evidence` is the stricter window-completeness measure. Neither metric converts partial or child-result rows into verified decisions.

## Finding

`backward_12` is the smallest tested strategy meeting the exploratory 98% target on complete cited evidence for verified decisions (42/42).

Across all 50 adjudicated rows, including partial and child-result cases, `lineage_backward_12` is strongest: 49/50 contain every cited source turn and all 50 contain at least one, while removing 93.0% of the temporal search universe. The lone incomplete row is partial rather than a verified source.

Plan-mode anchoring did not improve cited-evidence recall over the five-turn fallback (43/50 versus 43/50). Plan mode remains a useful ranking signal, but the nearest Plan turn is not a safe stopping boundary for high-recall context expansion.

The search-universe denominator is the per-decision set of repository turns eligible under the existing 72-hour temporal rule. The source denominator is the causally prior selected logical task plus traversable parent lineage. Counts are micro-averaged across 50 decision retrieval instances, so a turn may count once for each decision that could have retrieved it.

## Limits

- The same 50 rows were used to motivate and evaluate these structural variants; a held-out cohort is required before treating the best setting as stable.
- Gold evidence marks the manually cited source turns, not every possibly useful context turn.
- Turn-count reduction does not model token length; long and short turns have equal weight.
- The cohort has 42 strict positives and no reviewed negatives, so this remains a retrieval experiment rather than classifier training evidence.

## Reproducibility

- Gold rows: 50
- Gold sample hash: `73b2dc2de7967859c9b138a6fbd56b9b10774a453bc5d3ba7b76c6c7795179a6`
- Parsed repository rollouts: 932
- Parsed turn blocks: 4455
- Plan lookback cap: 12 turns
- Fallback lookback: 5 turns
- Parent depth cap: 2
