# 100-decision alignment experiment — execution record

This is a completed empirical run, not a production retrieval contract or a
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

The new cases were split by whole *candidate logical session* into 33
development and 20 held-out decisions. No held-out candidate session appeared
in the original gold set. A post-label source-lineage check found one actual
source group crossing both development and historical groups; four held-out
rows are affected. Two reviewers received independent private
packets. A five-case pilot showed that wholly blind source searches were too
slow for this cohort, so remaining reviews may use the frozen matcher candidate
as a **hint**, not as proof. Each review records `review_mode` as either
`blind_source_search` or `candidate_assisted`; reviewers must still check
causally prior raw messages and preserve exact source ordinals. Their judgments,
source coordinates, disagreements, and adjudication are distinct fields; an
absent judgment stays absent rather than being converted to a negative.
Held-out labels and candidate coordinates are not for tuning.

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

`iteration_gate.py` enforces the frozen-development-ID check, rejects a
verified-source or 20-turn-evidence recall regression, and implements the
two-consecutive-plateau / six-attempt stop. It consumes *measured* iterations;
it does not run a search itself or authorize tuning on held-out labels.

The baseline staged scorer (`evaluate_staged_retrieval.py`) implements the
read order as top three ranked spans **inside** the 20-turn envelope, then the
rest of that envelope, then a lineage/source-scope expansion. Its
`first_complete_stage` uses gold citations to measure *oracle* coverage; it is
not a deployable stopping rule. On the original 50 rows, 39 of 42 verified
sources are fully cited in the top three spans and 42 of 42 in the 20-turn
envelope. Restricted to the 47 typed Decisions, these counts are 37 of 39 and
39 of 39. The three historical Documentation records remain present as
controls but are not strict-decision recall cases. The corrected token proxy
run measured 16,294,581 normalized tokens for full logical sessions,
3,684,056 for 20-turn envelopes, 1,062,677 for ranked top-three spans, and
595,993 for cited evidence-turn approximations across 50. Raw text-channel tool
outputs, counted separately, added 125,843,848, 31,900,429, 8,474,944,
and 4,406,578 tokens respectively. The combined per-message proxy totals are
therefore 142,138,429, 35,584,485, 9,537,621, and 5,002,571. Opaque
multimodal encodings embedded in plain text may be included in the raw-output
component, so these combined numbers are rough upper/contaminated proxies,
not confirmed readable chat text. This is an
approximately 93% reduction from full-session to top-three-span payload, but
it is not a safe cutoff: top three held all cited evidence for only 39/42
historically verified records, while the 20-turn envelope held 42/42.
These totals sum a hypothetical read for **each decision**; sessions reused by
multiple decisions are counted again, so they are not the unique storage size
of the whole Codex corpus.
"20-turn envelope" is the existing strategy's parameter: up to 20 backward
turns around each traversed task/parent anchor, plus the fixed local candidate
radius. It is **not** a guarantee of exactly 20 total turns per decision.
The ranker's query uses the *already-written* decision title; this is a
retrospective decision-to-source alignment tool, not a prospective candidate
detector that can rely on a future decision record.

## Token measurement contract

The local evaluator counts a fixed serialized normalized-message payload with
an explicitly supplied local tokenizer. For each decision it reports: the
entire selected rollout, the causal portion of that rollout, bounded source
lineage, the 20-turn envelope, the top three ranked spans, and the minimum
adjudicated useful messages where message ordinals exist. It also distinguishes
deduplicated content from repeated staged reads. These are **proxy tokens**, not
Codex billed tokens. Encrypted reasoning is unavailable. The corrected evaluator
also counts raw tool-output payloads separately for each stage; the normalized
ranking text remains unchanged. A source whose evidence uses excluded material
must carry that limitation rather than a falsely precise cost. The historical
`minimal_useful_content` figure mostly counts *all messages in cited turns*,
not exact minimal message snippets; the new adjudication must mark exact
message ordinals where possible.

## Future hosted use — not implemented here

Stable source coordinates may later support a curated-decision-first answer to
“why?”, with an owner-authorized raw-history fallback only while the applicable
retention window remains open. The proposed 30-day period is an example, not an
implemented retention policy. Raw evidence must not become visible to another
member or a project lead; the curator's bounded machine read is a separate
constitutional allowance. Expired, unavailable, or withdrawn evidence needs
an explicit state, never an invented citation. This experiment adds no hosted
storage, permission, or retention behavior.

## Final results and held-out boundary

Two independent reviewers completed all 33 development rows. Explicit
adjudication produced 27 verified sources, two partial, and four unresolved;
unresolved is **not** a negative label. One verified source is in a different
rollout from the frozen matcher candidate. The original matcher plus the
20-turn envelope contained all cited evidence for 24/27 verified decisions;
top-three lexical spans inside it contained all evidence for 22/27. A
development-only fallback including one recent neighboring session and one
text-relevant neighboring session contained all cited evidence for 27/27.
The same 27/27 coverage with ten recency neighbors retained 2,433 turns across
the 33 decisions after union with the initial scope; the hybrid retained 2,099.
Ranked short spans plus the
original envelope retained 811 turns at ten spans but fell to 26/27, so the
short view cannot replace the full fallback. If invoked only for the three
known baseline misses, the full hybrid would raise the total from 613 to 823
turns, but that is a **gold-oracle** cost calculation, not a deployable
automatic stop rule.

On the 33 development rows, local normalized-text proxy tokens total
12,097,692 for full selected logical sessions, 2,265,636 for the 20-turn
envelopes, 614,611 for top-three spans, and 21,103 for adjudicated exact
useful-message references. Raw tool-output text-channel proxies add
82,427,567, 18,228,774, 4,865,104, and 22,919 respectively. These are
per-decision repeated reads, not unique corpus storage or billed tokens;
opaque multimodal encodings inside text may inflate the raw-output component.
Exact cited messages are a lower bound on the surrounding context a curator
would need to interpret them.

`cohort-100/frozen-retrieval-setting.json` records the development-selected
read order before held-out labels were opened. Source misses had two concrete
causes: a preceding voice-chat session without a parent link, and a relevant
projectless session excluded by repository-only candidate filtering. The
held-out 20 were scored without tuning this rule. Candidate-session grouping
did not prove source-session separation: `check_source_leakage.py` found one
actual source-lineage group crossing groups, affecting four held-out rows.
The overlap was reported, not repaired by tuning. One supplemental
unresolved-case search was discarded because a broad
raw-log search surfaced embedded evaluator-style transcript material; it
contributed no independent judgment or gold label.

The development-only fallback token run reports 5,593,819 normalized tokens
for the initial scope plus one recent neighbor, 7,903,937 for the initial
scope plus the recent-plus-text hybrid, and 8,169,517 for the initial scope
plus ten recent neighbors, versus 2,265,636 for the initial 20-turn scope.
The hybrid ranked-to-ten short view is 4,862,125 tokens but misses one
verified source. A gold-oracle expansion of the hybrid *only* for the three
known initial misses would be 3,320,007 tokens; this is a hypothetical cost,
not an implemented sufficiency detector. Raw tool-output text proxies add
39,639,943, 46,575,550, 62,994,550, 28,145,672, and 20,566,232 tokens
to those five stages respectively; encoded payloads inside text can inflate
them. `cohort-100/development-evaluation/ITERATION-MEASUREMENTS.json` records
four measured strategy comparisons on the same development IDs. The
predeclared gate accepts the two recall gains and stops after ten-neighbor
expansion yields no gain and short ranking loses one verified source. Runtime
was not consistently measured and is recorded as unknown, not zero.

Held-out adjudication yielded 16 verified, one partial, two child-result-only,
and one unresolved. The unresolved candidate pointed to this live root task's
rollout; both reviewers excluded it rather than allowing task discussion to
contaminate the test. The frozen initial scope held all cited evidence for
16/16 verified held-out decisions; the first three ranked spans held it for
13/16. The source-group-clean subset has 14 verified decisions, with 14/14 in
the initial scope and 13/14 in the top three spans. The full analysis, token
totals for all 100 typed decisions, and limitations are in `COHORT-100-REPORT.md`.
