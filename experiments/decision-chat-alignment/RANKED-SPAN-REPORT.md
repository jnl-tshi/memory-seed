# Ranked short-span decision retrieval

## Method

The frozen Codex-only 50-decision gold cohort and previously measured lineage plus 12-turn envelope are reused. Candidate spans contain up to three adjacent turns from one logical task. Turns and messages after the decision-record minute are excluded. Queries use the decision title or full final record. Gold evidence coordinates are read only after ranking. Recency, lexical overlap, isolated cue variants, and a combined phase variant are compared. Cues affect ranking only.

| Strategy | Any evidence /50 | All evidence /50 | Verified complete /42 | Mean turns | Turn reduction vs causal envelope | Character reduction vs causal envelope |
|---|---:|---:|---:|---:|---:|---:|
| pool | 50 | 49 | 42 | 11.4 | 0.0% | 0.0% |
| recency top 1 | 37 | 24 | 21 | 1.0 | 91.2% | 83.0% |
| lexical top 1 | 44 | 29 | 26 | 1.4 | 87.5% | 78.0% |
| full record top 1 | 46 | 39 | 36 | 2.8 | 75.7% | 63.0% |
| boundary top 1 | 46 | 32 | 29 | 1.9 | 83.6% | 77.7% |
| plan top 1 | 43 | 29 | 26 | 1.6 | 85.9% | 75.2% |
| review top 1 | 41 | 29 | 26 | 1.9 | 83.6% | 73.2% |
| origin top 1 | 44 | 29 | 26 | 1.4 | 87.5% | 78.0% |
| phase top 1 | 40 | 29 | 26 | 2.3 | 79.4% | 70.1% |
| recency top 2 | 45 | 33 | 30 | 2.0 | 82.7% | 75.8% |
| lexical top 2 | 48 | 37 | 34 | 2.4 | 78.9% | 70.1% |
| full record top 2 | 46 | 40 | 37 | 3.3 | 71.1% | 60.1% |
| boundary top 2 | 47 | 38 | 35 | 3.0 | 73.6% | 63.9% |
| plan top 2 | 45 | 36 | 33 | 2.6 | 77.3% | 67.4% |
| review top 2 | 43 | 34 | 31 | 2.8 | 75.4% | 64.5% |
| origin top 2 | 48 | 37 | 34 | 2.4 | 78.9% | 70.1% |
| phase top 2 | 42 | 32 | 29 | 3.5 | 69.2% | 57.2% |
| recency top 3 | 47 | 39 | 36 | 2.9 | 74.5% | 65.4% |
| lexical top 3 | 50 | 42 | 39 | 3.3 | 71.1% | 64.0% |
| full record top 3 | 47 | 40 | 37 | 3.7 | 67.1% | 56.4% |
| boundary top 3 | 48 | 40 | 37 | 4.1 | 64.1% | 52.5% |
| plan top 3 | 47 | 39 | 36 | 3.4 | 70.1% | 61.8% |
| review top 3 | 44 | 36 | 33 | 3.6 | 68.0% | 59.4% |
| origin top 3 | 50 | 42 | 39 | 3.3 | 71.1% | 64.0% |
| phase top 3 | 44 | 34 | 31 | 4.3 | 61.8% | 47.5% |

## Interpretation

The best tested three-span setting is title lexical overlap: 39/42 verified decisions retain every cited turn (92.9%), with 64.0% fewer parsed characters than the causal envelope. That is below the exploratory 98% complete-evidence target. A full final-record query is stronger for a single span (36/42 versus title-only 26/42), but weaker at three spans (37/42 versus 39/42); more query text is not a uniformly better ranker. The combined phase-cue score retains only 31/42 at three spans. These figures support using ranking to prioritize inspection, not to discard the rest of the envelope.

The next bounded test should inspect the three title-lexical misses at message level, then trial adaptive expansion: inspect the highest-ranked spans first, expand backward/through lineage when evidence is incomplete, and retain the 12-turn envelope as a fallback. The tool-heavy-then-user cue is only a possible round boundary; this experiment did not establish that implementation was complete at those points. The origin field is too sparse in this cohort to judge its value.

The causal envelope is the recall ceiling for these ranking variants. A gold turn can be counted even if the cited message is later in a long turn; future work should evaluate message-level provenance before treating turn recall as curator-ready context.

This is a development-cohort ablation. The 50 rows informed the feature choices. A held-out cohort is needed before adopting weights or a cutoff. The envelope starts from the previously selected session, so the result does not measure end-to-end session finding. Full final records may echo source wording, so their lexical advantage cannot be transferred to prospective decision detection. Review language identifies relevant context but cannot by itself identify a reviewer agent. Character counts measure retained parsed message text, not billed tokens or the curator's exact input.

## Provenance

Sample hash: `73b2dc2de7967859c9b138a6fbd56b9b10774a453bc5d3ba7b76c6c7795179a6`. Coordinate-level results are in `RANKED-SPAN-RESULTS.json`. No raw chat or reasoning text is written to either artifact.
