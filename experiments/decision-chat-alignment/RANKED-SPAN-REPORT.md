# Ranked short-span decision retrieval

## Method

The frozen Codex-only 50-decision gold cohort is reused. A lineage-aware 20-turn lookback defines the safety envelope: up to 20 preceding turns plus the anchor in each selected/parent task, with the fixed-radius union able to add turns. The earlier 12-turn strategy remains in WINDOW-STRATEGY-RESULTS.json for direct comparison. Candidate spans contain up to three adjacent turns from one logical task. Turns and messages after the decision-record minute are excluded. Queries use the decision title or full final record. Gold evidence coordinates are read only after ranking. Recency, lexical overlap, isolated cue variants, and a combined phase variant are compared. Cues affect ranking only.

| Strategy | Any evidence /50 | All evidence /50 | Verified complete /42 | Mean turns | Turn reduction vs causal envelope | Character reduction vs causal envelope |
|---|---:|---:|---:|---:|---:|---:|
| pool | 50 | 50 | 42 | 16.2 | 0.0% | 0.0% |
| recency top 1 | 37 | 24 | 21 | 1.0 | 93.8% | 87.3% |
| lexical top 1 | 43 | 29 | 26 | 1.5 | 91.0% | 83.0% |
| full record top 1 | 45 | 38 | 35 | 2.8 | 83.0% | 71.1% |
| boundary top 1 | 45 | 32 | 29 | 1.9 | 88.3% | 82.8% |
| plan top 1 | 41 | 28 | 25 | 1.7 | 89.5% | 80.7% |
| review top 1 | 40 | 29 | 26 | 1.9 | 88.3% | 79.4% |
| origin top 1 | 43 | 29 | 26 | 1.5 | 91.0% | 83.0% |
| phase top 1 | 38 | 28 | 25 | 2.4 | 85.5% | 76.4% |
| recency top 2 | 45 | 33 | 30 | 2.0 | 87.9% | 81.9% |
| lexical top 2 | 47 | 37 | 34 | 2.4 | 85.1% | 77.5% |
| full record top 2 | 45 | 39 | 36 | 3.3 | 79.4% | 68.4% |
| boundary top 2 | 46 | 38 | 35 | 3.0 | 81.5% | 72.9% |
| plan top 2 | 43 | 35 | 32 | 2.7 | 83.6% | 75.4% |
| review top 2 | 42 | 34 | 31 | 2.8 | 82.6% | 73.3% |
| origin top 2 | 47 | 37 | 34 | 2.4 | 85.1% | 77.5% |
| phase top 2 | 40 | 31 | 28 | 3.5 | 78.4% | 67.2% |
| recency top 3 | 47 | 39 | 36 | 2.9 | 82.1% | 74.1% |
| lexical top 3 | 49 | 43 | 39 | 3.4 | 79.3% | 72.6% |
| full record top 3 | 47 | 40 | 37 | 3.9 | 76.2% | 65.3% |
| boundary top 3 | 47 | 41 | 37 | 4.1 | 74.9% | 64.0% |
| plan top 3 | 45 | 38 | 35 | 3.5 | 78.3% | 71.1% |
| review top 3 | 43 | 37 | 33 | 3.7 | 77.1% | 69.4% |
| origin top 3 | 49 | 43 | 39 | 3.4 | 79.3% | 72.6% |
| phase top 3 | 43 | 33 | 30 | 4.6 | 71.9% | 59.2% |

## Interpretation

The 20-turn safety envelope retains all cited turns for 50/50 cases, compared with 49/50 at 12 turns; both retain 42/42 verified sources. It averages 17.9 turns and removes 90.2% of the eligible search universe. This is a larger safety margin, not a measured improvement on the verified subset.

The title-lexical top three retain every cited turn for 39/42 verified decisions, with 72.6% fewer parsed characters than the 20-turn envelope. A full final-record query retains 35/42 in one span versus title-only 26/42, and 37/42 in three spans. The combined phase-cue score retains 30/42 at three spans. These figures support using ranking to prioritize inspection, not to discard the rest of the envelope.

The next bounded test should inspect title-lexical misses at message level, then trial adaptive expansion: inspect the highest-ranked spans first, widen to the entire 20-turn safety envelope when evidence is incomplete, and only then extend farther back through lineage if needed. The tool-heavy-then-user cue is only a possible round boundary; this experiment did not establish that implementation was complete at those points. The origin field is too sparse in this cohort to judge its value.

The causal envelope is the recall ceiling for these ranking variants. A gold turn can be counted even if the cited message is later in a long turn; future work should evaluate message-level provenance before treating turn recall as curator-ready context.

This is a development-cohort ablation. The 50 rows informed the feature choices. A held-out cohort is needed before adopting weights or a cutoff. The envelope starts from the previously selected session, so the result does not measure end-to-end session finding. Full final records may echo source wording, so their lexical advantage cannot be transferred to prospective decision detection. Review language identifies relevant context but cannot by itself identify a reviewer agent. Character counts measure retained parsed message text, not billed tokens or the curator's exact input.

## Provenance

Sample hash: `73b2dc2de7967859c9b138a6fbd56b9b10774a453bc5d3ba7b76c6c7795179a6`. Coordinate-level results are in `RANKED-SPAN-RESULTS.json`. No raw chat or reasoning text is written to either artifact.
