# 100-decision alignment experiment — execution record

This is an in-progress empirical run, not a production retrieval contract or a
classifier-training set. The frozen original cohort contains 50 Codex-tagged
records, of which 47 are currently typed `Decision` and three are typed
`Documentation`. Those three remain in the historical audit but are excluded
from strict decision recall. A seeded sample of 53 previously unseen, typed
Codex Decisions brings the strict cohort to 100.

## Frozen inputs and sampling

- Original cohort: `results-codex-causal-minute-fixed/alignments.json` and
  `GOLD-SET.jsonl`; no original IDs or labels were changed.
- New population: typed Codex Decision records in the local Memory Seed
  sessions, excluding all 50 original IDs. The eligible population had 515
  records before the exclusion and 468 after it.
- New sample: `random.Random(20260925).sample` over sorted eligible IDs.
  `cohort-100/manifest.json` records all sampled IDs, the sample hash,
  repository revision, sampler hash, and Python version.
- No synthetic decisions, paid API, decision-record mutation, or raw-log edit.

## Retrieval and review boundary

The existing turn-aware matcher searched 935 temporally eligible Codex
rollouts and 4,483 normalized turn blocks for the 53 new decisions. It returned
6 High, 24 Medium, 22 Low, and 1 No-match outcomes. These categories are
heuristic candidate ranks, **not verified source labels**. Thirty candidate
windows being High/Medium does not mean thirty decisions were correctly
aligned.

The new cases are split by whole *candidate logical session* into 33
development and 20 held-out decisions. No held-out candidate session appeared
in the original gold set. The split is provisional until reviewers establish
actual source sessions; if an actual source crosses groups, leakage must be
reassessed before final scoring. Two reviewers receive independent, candidate-
blind private packets. Their judgments, source coordinates, disagreements,
and adjudication are distinct fields; an absent judgment stays absent rather
than being converted to a negative. Held-out labels and candidate coordinates
are not for tuning.

## Predeclared improvement loop

1. Freeze the sampled IDs, split, starting matcher, and original 50-case
   evidence. Independently verify development cases and adjudicate differences.
2. Measure source-session retrieval, all-evidence recall in the 20-turn
   lineage-aware envelope, top-ranked short-span recall, token volumes, and
   observed search/runtime cost. Count verified, partial, wrong, and unresolved
   separately; do not collapse them into accuracy.
3. Investigate each development miss by source coordinates and causal search
   path. Change one deterministic feature or search boundary at a time, up to
   six measured iterations. Re-run the frozen development cohort after each
   change. Reject a change that loses verified-source recall merely to save
   tokens. Stop after two consecutive iterations that recover no additional
   verified source and improve neither payload tokens nor runtime by at least
   5% at unchanged recall.
4. Freeze the winning setting before opening held-out judgments. Run it once
   on the 20 held-out decisions, report confidence intervals/denominators and
   unresolved cases, and do not tune on the held-out result.

## Token measurement contract

The local evaluator counts a fixed serialized normalized-message payload with
an explicitly supplied local tokenizer. For each decision it reports: the
entire selected rollout, the causal portion of that rollout, bounded source
lineage, the 20-turn envelope, the top three ranked spans, and the minimum
adjudicated useful messages where message ordinals exist. It also distinguishes
deduplicated content from repeated staged reads. These are **proxy tokens**, not
Codex billed tokens. Encrypted reasoning and currently unnormalized tool
outputs are not counted. A source whose evidence uses excluded material must
carry that limitation rather than a falsely precise cost.

## Future hosted use — not implemented here

Stable source coordinates may later support a curated-decision-first answer to
“why?”, with an owner-authorized raw-history fallback only while the applicable
retention window remains open. The proposed 30-day period is an example, not an
implemented retention policy. Raw evidence must not become visible to another
member or a project lead; the curator's bounded machine read is a separate
constitutional allowance. Expired, unavailable, or withdrawn evidence needs
an explicit state, never an invented citation. This experiment adds no hosted
storage, permission, or retention behavior.

## Status and limitations

Retrieval and split preparation have run. Independent review, adjudication,
message-level minimum-context labels, iterative tuning, and held-out scoring
are still pending. Candidate-session grouping cannot by itself prove
source-session separation; this will be checked against verified source refs.
