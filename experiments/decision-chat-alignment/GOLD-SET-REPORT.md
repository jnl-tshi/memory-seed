# First decision-source gold set

## Outcome

All 50 decisions in the frozen Codex cohort were manually adjudicated against causally prior retained
Codex evidence. Review started at the decision-time anchor and selected candidate region, searched
backward through the logical task, and followed child-to-parent lineage with the parent cutoff fixed
at child creation time.

The resulting labels are:

| Gold label | Count | Meaning |
|---|---:|---|
| Verified source | 42 | Causally prior retained evidence establishes the complete decision. |
| Partial multi-turn | 6 | Genuine source evidence exists, but a substantive part or adoption remains unverified. |
| Child result | 2 | A child agent produced substantive evidence, but it is not the originating parent discussion. |
| Wrong candidate | 0 | No row was left as a different-decision match after traversal. |
| Unresolved | 0 | Every row had at least some adjudicable retained evidence. |

The 42 verified rows are the first strict positive set. The six partial rows and two child-result rows
remain separately labeled and should not be silently promoted to equivalent positives.

## Candidate quality

- The matcher's winning turn directly describes the decision for 43 of 50 rows (86%).
- The returned bounded window contains at least one cited causal evidence item for all 50 rows
  (100%). This is window evidence coverage, not proof that the complete decision is inside the window.
- All cited evidence is inside the returned window for 42 of 50 rows (84%).
- Among the 42 fully verified decisions, 39 contain all cited evidence inside the returned window;
  three require deeper backward traversal.
- The only row with no cited evidence in the returned window is partial rather than absent: related
  evidence exists elsewhere in the same retained task.

Confidence is directionally useful but not a correctness boundary:

| Matcher confidence | Rows | Verified sources | Winning turn describes decision |
|---|---:|---:|---:|
| High | 6 | 6 | 6 |
| Medium | 25 | 22 | 22 |
| Low | 19 | 14 | 15 |

## Interpretation

The deterministic retrieval stage is now a credible high-recall candidate generator. Its bounded
window surfaced some causal evidence for 100% of this cohort, including many Low-confidence rows.
However, only 84% of rows contain every cited evidence item inside that window, and 86% of winning
turns directly describe the decision. The curator or a verification stage still needs backward
multi-turn and lineage traversal.

This gold set supports evaluation of candidate retrieval. It is not yet sufficient for a final local
classifier: 42 strict positives are useful for a first baseline but too small for a stable grouped
train/test estimate, and safe reviewed negatives are still absent.

## Integrity controls

- Every row preserves the frozen decision ID, selected rollout ID, selected turn, evidence ordinals,
  timestamps, source roles, and parent hops.
- Raw chat excerpts and encrypted reasoning are excluded from tracked artifacts.
- `assemble_gold_set.py` refuses missing, duplicate, extra, candidate-drifted, or untraversed evidence
  rollout references.
- Negative-control tests deliberately corrupt a winning turn and remove a cohort row; both must fail.
- `GOLD-SET.jsonl` is the canonical machine-readable artifact; `GOLD-SET.csv` is the compact review
  projection. The three files under `gold-parts/` preserve audit-batch provenance.
