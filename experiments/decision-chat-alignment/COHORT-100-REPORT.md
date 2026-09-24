# Codex decision-to-chat alignment: strict 100-decision extension

Status: read-only research experiment, isolated branch. No decision records,
Codex rollouts, production Memory Seed pipeline, hosted retention rule, or
classifier were changed. The retrieval setting was selected on development
rows and frozen before either held-out review packet was opened.

## Question and design boundary

Can existing Codex-authored Memory Seed decisions be linked to the raw turns
that explain them, with substantially less material read than a whole session?
This is **retrospective decision-to-source alignment**, not a prospective
decision-candidate detector. The decision title and record text are known to
this retriever, so its scores cannot be reported as detector recall.

The design premise remains: generic atomic-fact extraction is not a mandatory
stage. Its useful feature is decomposition into what/why/alternatives/constraints/
evidence/consequences/earlier-decision links. A cheap deterministic detector
may later over-detect decision-like spans; a local classifier may then reduce
volume, but both must optimize for missed-decision risk. The curator retains
semantic judgment, and every accepted record needs raw-session/turn/message
provenance.

## Cohort and audit method

- The earlier seeded 50-row Codex-tagged audit contained 47 typed Decisions and
  three Documentation controls. We kept that audit unchanged and sampled 53
  unseen typed Codex Decisions from 468 eligible unseen records using
  `random.Random(20260925).sample` over sorted IDs. This yields exactly 100
  typed Decisions plus the three historical controls. The frozen 53-ID hash
  and population details are in `cohort-100/manifest.json`.
- The 53 were split into 33 development and 20 sealed rows by candidate
  logical-session group. Two independent small-model reviewers inspected raw
  pre-record evidence for each new row; an explicit adjudication selected
  source citations or an unresolved label. The assembler verified cited raw
  ordinals and timestamps against the local JSONL and rejected post-cutoff
  evidence. Raw transcript text and private reviewer packets were not tracked.
- Source timestamps must precede the recorded decision minute plus one minute.
  This minute allowance reflects the session-record timestamp precision; it
  is not proof that the source choice occurred at write time. The parser keeps
  root and child rollouts separate and follows parent lineage when a bounded
  source window requires it. Readable reasoning summaries may be searched;
  encrypted reasoning is unavailable.
- The initial safety scope is the existing lineage-aware backward-20 strategy:
  up to 20 earlier turns per traversed anchor, plus the fixed local candidate
  radius. It is not always exactly 20 total turns. Lexically ranked short spans
  *inside* that scope are read first; the remaining safety scope is next.
  Development-only misses motivated one recent and one text-relevant nearby
  session as a final fallback, including voice and projectless origins.
  `cohort-100/frozen-retrieval-setting.json` fixes this order before held-out
  labels. The neighboring-session stage must be **unioned with** the initial
  20-turn scope; an isolated neighbor result can otherwise lose existing
  evidence.

The staged “first complete” point below is a **gold-oracle measurement**:
citations tell the evaluator when evidence is complete. No automatic semantic
sufficiency detector has been implemented. A curator could decide to expand;
the experiment does not prove how reliably or cheaply that decision can be
made without reading more.

## Source-audit result

| Cohort | Typed Decisions | Verified source | Partial | Child result only | Unresolved |
| --- | ---: | ---: | ---: | ---: | ---: |
| Historical strict subset | 47 | 39 | 6 | 2 | 0 |
| New development | 33 | 27 | 2 | 0 | 4 |
| New held-out | 20 | 16 | 1 | 2 | 1 |
| **Strict total** | **100** | **82** | **9** | **4** | **5** |

“Verified” means the adjudicated cited turns explain the recorded choice,
not that the frozen top-ranked candidate alone is correct. “Partial” retains
some relevant evidence without claiming the entire record is established.
“Child result” is evidence from a reviewer/worker without independently
establishing parent adoption. Unresolved is **unlabeled**, never a negative.
For the new 53, the adjudicators marked the selected candidate as describing
the decision in 41 cases, false in 11, and indeterminate in one. Thus a
candidate appearing for every sampled record is not the same as verified
candidate correctness.

The held-out reviewers disagreed materially: reviewer A reported 16 verified,
two child results, one partial and one unresolved; reviewer B reported seven
verified, four partial and nine unresolved. Their search breadth differed.
Adjudication preferred exact earlier parent/user/implementation citations when
they directly established the choice, and retained partial/child labels where
the cited content did not establish every step. Representative disputed raw
ordinals were reopened before selection; the assembler mechanically validated
every selected coordinate and cutoff. This is an **AI-adjudicated provisional
gold set**, not a claim of independent human agreement.

## Frozen retrieval results

The metric is complete coverage of **all adjudicated cited evidence turns**
for a verified decision. It does not count partial, child-only, or unresolved
rows as verified successes or false negatives.

| Stage | Development verified | Held-out verified | Source-group-clean held-out verified |
| --- | ---: | ---: | ---: |
| First three lexical spans inside initial scope | 22/27 | 13/16 | 13/14 |
| Full initial lineage-aware 20-turn scope | 24/27 | 16/16 | 14/14 |
| Initial scope plus frozen nearby-session fallback | 27/27 | 16/16 | 14/14 |

On development, the fallback recovered three misses: two source choices were
in a preceding voice-chat session without a parent edge to the frozen
candidate, and one was in a projectless session excluded by repo-only search.
Ten recent neighbors found no additional verified source compared with the
one-recent/one-text hybrid. A short ranked fallback lost one development
source, so ranking is an inspection order, not a hard cutoff. The measured
development iteration gate accepted two source-recall gains, then stopped
after two consecutive non-improving trials; runtime was not measured
consistently and was not used as a gain. Details are in
`cohort-100/development-evaluation/ITERATION-MEASUREMENTS.json`.

The held-out 20-turn result requires two qualifications. One row's frozen
candidate was this live root conversation; both reviewers excluded it and
left it unresolved rather than contaminate the test. A post-label audit found
one actual source-lineage group shared with development **and** the historical
set, affecting four held-out rows (two verified, two child-result-only).
The untouched independent descriptive subset is therefore 15 rows, of which
14 have verified sources. Its 14/14 full-scope coverage is encouraging, but
too small and selected to validate a 98% operating threshold. The source
lineage overlap was reported, not used to retune the frozen rule.

The five unresolved strict records have different causes: two development
records' nested-runtime/append-only rules were not directly established in
the inspected candidate plus continuation; one specific promotion/disposition
choice was not recovered; another record was written before a visible shared
architecture conclusion; and the held-out live-task case was excluded. None
proves the source is absent from all Codex logs. Child results and partial
multi-turn records expose the additional difference between finding a review
finding, finding parent adoption, and explaining the full final record.

## Token-efficiency accounting

Counts use one pinned local Qwen tokenizer and a fixed serialized text
representation. They are **per-decision repeated-read proxies**, not unique
corpus storage, billable provider usage, or a measured end-to-end curator run.
The entire selected logical session is a comparison baseline, not guaranteed
to contain every parent/nearby source. Structured multimodal blocks and
encrypted reasoning are omitted. Raw tool-output text is counted separately;
opaque encodings inside text can inflate it.

| Strict 100 scope | Normalized chat tokens | Separate raw tool-output text proxy | Combined text-channel proxy |
| --- | ---: | ---: | ---: |
| Entire selected logical session | 29,461,733 | 214,117,241 | 243,578,974 |
| Initial 20-turn lineage scope | 7,095,529 | 54,563,921 | 61,659,450 |
| First three ranked spans | 1,998,358 | 15,304,592 | 17,302,950 |
| Exact cited message ordinals | 49,624 | 3,659 tool + 76 other events | 53,359 |

The initial scope reduces normalized text by about 76% against the selected
whole-session baseline; the first three spans reduce it by about 93%. Those
top-three spans still omit complete cited evidence for three of the 16
verified held-out decisions and five of the 27 verified development decisions.
The 53,359-token exact-citation total is a **manually identified lower bound**
on useful source text, not an achieved automatic curator payload. It counts
202 distinct cited raw ordinals over the strict 100 and includes an older
`item_completed` assistant-message event shape. The per-decision file is
`cohort-100/CITED-MESSAGE-TOKENS.json`.

The cohorts differ in baseline size: the 33 development selected sessions
total 12,097,692 normalized tokens and their initial scopes 2,265,636;
the 20 held-out selected sessions total 1,749,650 and their initial scopes
1,311,053. Thus a single aggregate compression rate hides large variation.
On development, the **union** of initial scope and one recent neighbor costs
5,593,819 normalized tokens and recovers 26/27 verified sources; the frozen
one-recent/one-text fallback costs 7,903,937 and recovers 27/27. Ten recent
neighbors cost 8,169,517 with no additional recovery. These are maximum
stage-scope comparisons, not the amount an agent would necessarily read after
a successful first pass. The gold-oracle conditional fallback would cost
3,320,007 development tokens if invoked only for the three *known* initial
misses, but no deployable sufficiency test identifies them yet.

## Dataset and architecture implications

The 82 verified decisions provide promising **positive** source windows with
provenance, but 18 strict records remain partial, child-only or unresolved.
No unlinked random window is a trustworthy negative: Memory Seed may have
missed decisions. A first detector baseline should use human-reviewed
high-confidence negatives sampled from execution/tool-heavy and ordinary
discussion regions, including hard near-miss windows. Split all windows by
actual root source session/parent lineage, and ideally reserve entire projects
after enough projects exist. Never put overlapping windows or sibling agents
from the same source group on opposite sides. The source-group overlap found
here shows candidate-session grouping alone is insufficient.

Do **not** train a TF-IDF/classifier baseline from this corpus yet: positives
are still AI-adjudicated, negatives are not curated, and the clean held-out
source groups are few. This experiment supports testing **B** (high-recall
deterministic candidate detector then curator) against **A** (whole raw
conversation to curator). It does not establish that **C** (classifier alone)
or **D** (rules then classifier then curator) improves the recall/cost tradeoff.
Plan-mode and reviewer-shaped signals should be weak ranking cues, not hard
eligibility rules: choices also surfaced in ordinary user turns, assistant
plans, implementation closeouts, parent sessions, and child review results.

The same exact source coordinates could later support an owner-authorized
hosted “why?” answer that begins with the structured decision and optionally
retrieves retained raw history. This experiment implements no hosted storage,
access control or retention policy. Raw history availability and curator
permission must be checked at answer time; absent or expired evidence must be
reported as unavailable rather than reconstructed as a citation.

## Smallest next experiment

Have a person audit the 15 source-group-clean held-out rows plus the five
unresolved records, concentrating on the AI-adjudication disagreements and
whether each cited span actually explains the decision. Then collect a small
prospective set (around 30 new decisions) with source session/turn/message
coordinates captured at write time and split by actual root source group.
Run the frozen top-three → full-20 → nearby fallback order with a blinded
curator sufficiency judgment and actual tokens read per stage. Only after
that, curate explicitly reviewed negatives and test a recall-first detector.
Thirty positives can reveal gross misses; they cannot statistically establish
98% recall. Do not tune on the sealed 20 after this report.

## Reproduction and privacy

The tracked `cohort-100/` artifacts contain decision IDs, labels, scores,
timestamps, hashed source-group audits, and raw-log coordinates, but no full
chat windows. Private review packets stay in the designated Temp directory.
`README.md` names the scripts; `cohort-100/frozen-retrieval-setting.json`
and the seeded manifest pin the pre-held-out rule and sample. `SOURCE-LEAKAGE-
RESULTS.json` intentionally exits nonzero when a split overlap is found.
