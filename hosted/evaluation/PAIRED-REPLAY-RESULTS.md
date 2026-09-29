# P0.2 paired decision-extraction replay results

Status: completed offline diagnostic; not evidence of autonomous decision-detection accuracy.

## Answer

The revised extractor did **not** demonstrate better semantic decision detection in this evaluation.
It retrieved substantially more of the cited evidence and avoided repeated extraction work, but neither
frozen arm produced a complete semantic match in the fourteen held-out cases according to either blind
reviewer. The revised arm also emitted candidates for only two of those fourteen cases. P0.2 therefore
remains incomplete: source retrieval improved, while actual issue/action/scope extraction remains
unvalidated and unsuccessful on this held-out sample.

## Frozen comparison

- Original parser: `1c3f2e298e95ae8c54dcc5918cbaf6d2e95e3003`.
- Revised parser: `95514648be7dae6652d217fd8bfbcade897e19d3`.
- Corpus: 67 eligible verified decisions, 65 replayable; 53 development and 14 held-out cases.
- Missing visible anchors: `mse_f29hkasxxz61ghw6:d1` and `mse_f82r85nq95zng55e:d1`.
- Both arms used the pinned spaCy backend. Production parser files were frozen during the experiment.

| 65 replayable cases | Original | Revised |
| --- | ---: | ---: |
| Cases with any draft | 65 | 5 |
| Cases with accepted-state draft | 11 | 3 |
| Cases with a complete draft | not implemented | 0 |
| All accessible cited refs retrieved | 19 | 60 |
| All cited refs retrieved, including inaccessible/tool refs | 15 | 51 |

For the fourteen held-out cases, the original arm emitted candidates in 14 cases, emitted accepted-state
drafts in 3, and retrieved all cited refs in 5. The revised arm emitted candidates in 2 cases, emitted
accepted-state drafts in both, retrieved all cited refs in all 14, and produced zero complete drafts.

## Blind semantic review

Two independent read-only reviewers saw masked arms, frozen candidate meanings, the gold record, and the
supplied source evidence for every held-out case. Neither saw parser code, the arm mapping, raw results,
or aggregate results. This is descriptive AI review, not human gold.

Both reviewers found **zero complete semantic matches for both arms**. The revised candidates in the two
cases where they existed had grounded acceptance, but issue, action, and scope were insufficient in both,
and material conditions differed in both. The original arm had one consensus-equivalent action across
fourteen candidate-bearing cases, but issue and scope were insufficient in all fourteen; false or
misattributed acceptance and missing conditions were common.

Field counts in `semantic-results.json` are conservative consensus counts. A label is counted only when
both reviewers agreed; disagreements remain `conflict` rather than being forced into a held-out
adjudication. Candidate-index disagreements and both original vectors are preserved. No extractor rule
was changed from these results.

## Retained-state ablation

The revised parser's retained-state and repeated-reparse variants produced identical normalized outputs
for all 65 replayable cases. Retained-state extraction made 5,669 extraction calls versus 14,339 for
reparse (60.5% fewer) and processed 2,594,386 input characters versus 6,086,846 (57.4% fewer).
This establishes reduced repeated processing, not a wall-clock speedup; linguistic-feature memoization
was shared by both ablation arms.

## Instrument checks

- The two complete private replay runs are byte-for-byte identical, including all 65 masked packets.
- Every replayed row passes the post-run gold identity and heading guard; no saved gold bytes differ.
- Every first-run masked packet exactly matches its corresponding frozen private review payload.
- The committed public cases exactly equal the private cases after removing raw drafts and review evidence.
- All 65 retained-state/reparse output comparisons are identical after excluding instrumentation.
- No cited-event set has a timestamp/source-ordinal inversion, and every selected anchor is the maximum
  source ordinal within its selected rollout.
- Both reviewers independently reached the same zero-complete-match conclusion for each arm.

These checks validate the measurement path. They do not convert the selected positive corpus into a
population test and do not supply a negative-control population for autonomous detection.

## Limits

- The replay uses an oracle source anchor at the last accessible cited visible event. It does not measure
  autonomous marker placement, discovery recall, or false-positive rate.
- No future messages are supplied, so this is anchor-time reconstruction rather than a full streaming wait.
- The revised arm may retrieve causally earlier parent lineage; retrieval and extraction rules therefore
  differ between the parser arms. Only the retained-state ablation isolates repeated processing.
- Fixed cue coverage was 10/65 at the oracle anchor and 34/65 at any cited visible event. That is cue
  coverage, not detector recall.
- The accepted-state marker is heuristic. Every output remains an inert draft requiring curator review.

## Disposition

The evidence supports two narrower claims: cited-evidence retrieval improved, and retained-state
processing avoided repeated work without changing outputs. It does not support a claim that semantic
decision detection improved. Further extraction work should be developed only on development cases and
evaluated in a new preregistered replay; the held-out cases must not be used for parser tuning.
