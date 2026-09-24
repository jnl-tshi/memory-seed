# Ranked short-span decision retrieval

## Method

The frozen Codex-only 50-decision gold cohort is reused. A lineage-aware 20-turn lookback defines the safety envelope: up to 20 preceding turns plus the anchor in each selected/parent task, with the fixed-radius union able to add turns. The earlier 12-turn strategy remains in WINDOW-STRATEGY-RESULTS.json for direct comparison. Candidate spans contain up to three adjacent turns from one logical task. Turns and messages after the decision-record minute are excluded. Queries use the decision title or full final record. Gold evidence coordinates are read only after ranking. Recency, lexical overlap, isolated cue variants, and a combined phase variant are compared. Cues affect ranking only.

| Strategy | Any evidence /50 | All evidence /50 | Verified complete /42 | Mean turns | Turn reduction vs causal envelope | Character reduction vs causal envelope |
|---|---:|---:|---:|---:|---:|---:|
| pool | 28 | 30 | 24 | 16.9 | 0.0% | 0.0% |
| recency top 1 | 26 | 20 | 16 | 1.0 | 94.1% | 87.7% |
| lexical top 1 | 27 | 22 | 17 | 1.5 | 91.1% | 82.9% |
| full record top 1 | 24 | 23 | 18 | 2.6 | 84.4% | 72.6% |
| boundary top 1 | 26 | 24 | 19 | 2.0 | 88.2% | 82.1% |
| plan top 1 | 22 | 19 | 15 | 1.9 | 88.7% | 79.7% |
| review top 1 | 24 | 20 | 15 | 1.9 | 88.6% | 81.9% |
| origin top 1 | 27 | 22 | 17 | 1.5 | 91.1% | 82.9% |
| phase top 1 | 19 | 20 | 16 | 2.4 | 85.7% | 77.6% |
| recency top 2 | 28 | 27 | 22 | 2.0 | 88.4% | 83.3% |
| lexical top 2 | 27 | 26 | 21 | 2.5 | 85.3% | 77.5% |
| full record top 2 | 25 | 25 | 20 | 3.2 | 81.0% | 71.5% |
| boundary top 2 | 26 | 26 | 21 | 3.2 | 81.4% | 75.8% |
| plan top 2 | 23 | 22 | 18 | 2.9 | 83.0% | 73.4% |
| review top 2 | 24 | 24 | 19 | 2.9 | 82.8% | 76.3% |
| origin top 2 | 27 | 26 | 21 | 2.5 | 85.3% | 77.5% |
| phase top 2 | 19 | 20 | 16 | 3.6 | 78.7% | 69.6% |
| recency top 3 | 28 | 28 | 23 | 2.9 | 82.6% | 77.4% |
| lexical top 3 | 27 | 27 | 22 | 3.4 | 80.1% | 73.0% |
| full record top 3 | 26 | 27 | 21 | 3.9 | 77.1% | 68.1% |
| boundary top 3 | 26 | 26 | 21 | 4.2 | 75.1% | 70.1% |
| plan top 3 | 23 | 23 | 19 | 3.8 | 77.8% | 69.8% |
| review top 3 | 24 | 24 | 19 | 3.8 | 77.3% | 69.3% |
| origin top 3 | 27 | 27 | 22 | 3.4 | 80.1% | 73.0% |
| phase top 3 | 21 | 22 | 18 | 4.6 | 72.6% | 62.2% |

## Interpretation

The 20-turn safety envelope retains all cited turns for 30/50 cases, compared with 30/50 at 12 turns; both retain 24/42 verified sources. It averages 18.6 turns and removes 89.9% of the eligible search universe. This is a larger safety margin, not a measured improvement on the verified subset.

The title-lexical top three retain every cited turn for 22/42 verified decisions, with 73.0% fewer parsed characters than the 20-turn envelope. A full final-record query retains 18/42 in one span versus title-only 17/42, and 21/42 in three spans. The combined phase-cue score retains 18/42 at three spans. These figures support using ranking to prioritize inspection, not to discard the rest of the envelope.

The next bounded test should inspect title-lexical misses at message level, then trial adaptive expansion: inspect the highest-ranked spans first, widen to the entire 20-turn safety envelope when evidence is incomplete, and only then extend farther back through lineage if needed. The tool-heavy-then-user cue is only a possible round boundary; this experiment did not establish that implementation was complete at those points. The origin field is too sparse in this cohort to judge its value.

The causal envelope is the recall ceiling for these ranking variants. A gold turn can be counted even if the cited message is later in a long turn; future work should evaluate message-level provenance before treating turn recall as curator-ready context.

This is a development-cohort ablation. The 50 rows informed the feature choices. A held-out cohort is needed before adopting weights or a cutoff. The envelope starts from the previously selected session, so the result does not measure end-to-end session finding. Full final records may echo source wording, so their lexical advantage cannot be transferred to prospective decision detection. Review language identifies relevant context but cannot by itself identify a reviewer agent. Character counts measure retained parsed message text, not billed tokens or the curator's exact input.

## Provenance

Sample hash: `e1fb0f77272bed5f17c11c11203ef330fa29fba6c718dc6062d7f97168b96dfb`. Coordinate-level results are in `RANKED-SPAN-RESULTS.json`. No raw chat or reasoning text is written to either artifact.
