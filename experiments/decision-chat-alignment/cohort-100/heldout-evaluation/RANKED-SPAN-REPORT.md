# Ranked short-span decision retrieval

## Method

The frozen Codex-only 50-decision gold cohort is reused. A lineage-aware 20-turn lookback defines the safety envelope: up to 20 preceding turns plus the anchor in each selected/parent task, with the fixed-radius union able to add turns. The earlier 12-turn strategy remains in WINDOW-STRATEGY-RESULTS.json for direct comparison. Candidate spans contain up to three adjacent turns from one logical task. Turns and messages after the decision-record minute are excluded. Queries use the decision title or full final record. Gold evidence coordinates are read only after ranking. Recency, lexical overlap, isolated cue variants, and a combined phase variant are compared. Cues affect ranking only.

| Strategy | Any evidence /50 | All evidence /50 | Verified complete /42 | Mean turns | Turn reduction vs causal envelope | Character reduction vs causal envelope |
|---|---:|---:|---:|---:|---:|---:|
| pool | 19 | 20 | 16 | 13.3 | 0.0% | 0.0% |
| recency top 1 | 19 | 13 | 9 | 1.0 | 92.5% | 83.4% |
| lexical top 1 | 17 | 13 | 9 | 1.2 | 91.0% | 80.1% |
| full record top 1 | 16 | 16 | 13 | 2.5 | 81.6% | 64.3% |
| boundary top 1 | 14 | 11 | 9 | 1.9 | 85.3% | 77.9% |
| plan top 1 | 15 | 13 | 10 | 1.6 | 88.3% | 76.6% |
| review top 1 | 15 | 13 | 10 | 1.6 | 87.6% | 79.3% |
| origin top 1 | 17 | 13 | 9 | 1.2 | 91.0% | 80.1% |
| phase top 1 | 11 | 10 | 9 | 2.2 | 83.1% | 74.2% |
| recency top 2 | 19 | 18 | 14 | 1.9 | 85.7% | 78.7% |
| lexical top 2 | 17 | 15 | 11 | 2.1 | 84.2% | 76.1% |
| full record top 2 | 16 | 16 | 13 | 3.2 | 75.9% | 55.9% |
| boundary top 2 | 15 | 14 | 11 | 3.1 | 76.3% | 70.4% |
| plan top 2 | 15 | 14 | 11 | 2.5 | 81.6% | 73.2% |
| review top 2 | 15 | 13 | 10 | 2.5 | 80.8% | 75.6% |
| origin top 2 | 17 | 15 | 11 | 2.1 | 84.2% | 76.1% |
| phase top 2 | 12 | 12 | 10 | 3.5 | 74.1% | 66.8% |
| recency top 3 | 19 | 19 | 15 | 2.8 | 78.9% | 74.5% |
| lexical top 3 | 18 | 17 | 13 | 3.0 | 77.1% | 70.8% |
| full record top 3 | 16 | 17 | 14 | 3.9 | 70.7% | 53.3% |
| boundary top 3 | 16 | 14 | 11 | 4.1 | 69.2% | 60.8% |
| plan top 3 | 16 | 16 | 13 | 3.5 | 73.7% | 68.7% |
| review top 3 | 16 | 15 | 12 | 3.5 | 73.7% | 70.4% |
| origin top 3 | 18 | 17 | 13 | 3.0 | 77.1% | 70.8% |
| phase top 3 | 13 | 13 | 11 | 4.6 | 65.4% | 58.6% |

## Interpretation

The 20-turn safety envelope retains all cited turns for 20/50 cases, compared with 20/50 at 12 turns; both retain 16/42 verified sources. It averages 14.8 turns and removes 89.8% of the eligible search universe. This is a larger safety margin, not a measured improvement on the verified subset.

The title-lexical top three retain every cited turn for 13/42 verified decisions, with 70.8% fewer parsed characters than the 20-turn envelope. A full final-record query retains 13/42 in one span versus title-only 9/42, and 14/42 in three spans. The combined phase-cue score retains 11/42 at three spans. These figures support using ranking to prioritize inspection, not to discard the rest of the envelope.

The next bounded test should inspect title-lexical misses at message level, then trial adaptive expansion: inspect the highest-ranked spans first, widen to the entire 20-turn safety envelope when evidence is incomplete, and only then extend farther back through lineage if needed. The tool-heavy-then-user cue is only a possible round boundary; this experiment did not establish that implementation was complete at those points. The origin field is too sparse in this cohort to judge its value.

The causal envelope is the recall ceiling for these ranking variants. A gold turn can be counted even if the cited message is later in a long turn; future work should evaluate message-level provenance before treating turn recall as curator-ready context.

This is a development-cohort ablation. The 50 rows informed the feature choices. A held-out cohort is needed before adopting weights or a cutoff. The envelope starts from the previously selected session, so the result does not measure end-to-end session finding. Full final records may echo source wording, so their lexical advantage cannot be transferred to prospective decision detection. Review language identifies relevant context but cannot by itself identify a reviewer agent. Character counts measure retained parsed message text, not billed tokens or the curator's exact input.

## Provenance

Sample hash: `e1fb0f77272bed5f17c11c11203ef330fa29fba6c718dc6062d7f97168b96dfb`. Coordinate-level results are in `RANKED-SPAN-RESULTS.json`. No raw chat or reasoning text is written to either artifact.
