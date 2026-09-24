# Memory Seed decision-to-chat alignment experiment

Date: 2026-09-24
Status: discovery complete; no production architecture changed

## Executive result

Existing Memory Seed decisions can sometimes be aligned to raw Codex conversation windows, but the
historical corpus is not currently linkable at a rate that supports automatic dataset construction.
In a reproducibly random sample of 50 decisions, the conservative matcher produced 0 High, 3 Medium,
10 Low, and 37 No-match results. The three Medium results were manually inspected and appear to be
real source windows. Counting only High and Medium, 3/50 (6%) were automatically aligned; 6/50 (12%)
had multiple plausible sessions.

The main constraint was not weak text similarity. Twenty-seven sampled decisions were recorded as
Claude-family work and therefore had no actor-compatible source in the Codex store being tested.
Among the 23 Codex-authored decisions, the result was 3 Medium, 10 Low, and 10 No match. This makes the
experiment evidence for a provenance-capture problem before it is evidence for or against a future
decision detector.

The immediate research direction should be a prospective, first-hand provenance sample, followed by
a recall-first deterministic detector evaluation. A learned classifier is premature because the
present positive set is too small and unlinked conversation is not a trustworthy negative class.

## 1. Design discovery summary

The architecture under investigation remains:

```text
raw conversation
-> high-recall decision-candidate detection
-> optional lightweight decision/non-decision classifier
-> curator semantic interpretation
-> structured Memory Seed decision
```

This experiment records the following conclusions:

1. Generic atomic-fact extraction is not a necessary mandatory stage. Extracting all facts before
   reconstructing decisions adds cost and complexity while most extracted facts are irrelevant.
2. The useful idea from atomic extraction is decomposition. Memory Seed needs decision-focused
   fields: what was decided, why, alternatives, constraints, evidence, consequences, and relations
   to earlier decisions.
3. Deterministic linguistic extraction is most promising as a candidate detector. Choosing,
   preferring, replacing, rejecting, changing direction, committing, settling, deferring, and
   deciding not to act are useful high-recall cues.
4. That deterministic layer should over-detect. It should say only that something decision-like may
   be happening nearby.
5. A small binary classifier may later separate decision-relevant from non-decision-relevant blocks.
6. Such a classifier could run locally at negligible marginal cost relative to an LLM classifier.
7. Decision recall, false-negative rate, and candidate-volume reduction are the primary metrics.
   Precision is secondary, and overall accuracy is not an appropriate primary objective.
8. Approximately 98% recall of known decisions is an exploratory target, not an accepted production
   threshold.
9. The curator remains responsible for implicit decisions, multi-turn reasoning, alternatives,
   rationale, supersession, ambiguity, and final decision boundaries.
10. An aligned example is usable only if it retains the source session and bounded source span.

## 2. Data discovery

### Memory Seed decisions

The authoritative human-readable records are Markdown beneath `.memory-seed/sessions/YYYY-MM/`.
There were 92 dated session files in the active runtime at the time of the experiment. The repository
also contains 61 accepted decision/ADR documents beneath `.memory-seed/decisions/`; these are a
separate design-authority layer and were not mixed into the sampled session-decision population.

The canonical parser in `memory_seed.retrieval.load_corpus` and `memory_seed.semantic_cache` turns
session Markdown into `MemoryChunk` records. Relevant fields include:

- `chunk_id`, `entry_id`, decision ordinal, `record_kind`, title, text, and heading path;
- `entry_datetime`/session date, source path, and start/end line;
- user, agent type, project/subproject path, branch, commits, and source references;
- tags, contexts, topics, related entries, replacements, evolutions, and decision edges.

The experiment population was every parseable canonical chunk whose `record_kind` was `Decision` and
that had an `entry_id`: 1,640 decisions. A decision identity was represented as
`<entry_id>:<decision ordinal>`. Documentation records and synthetic test fixtures were excluded.

The strongest potentially useful native link fields are agent type, timestamp, project path, branch,
commit SHA, source references, filenames, and decision/rationale text. Existing records generally do
not contain a Codex session ID or turn span.

### Codex conversation storage

The inspected local Codex store is `.codex/`. Raw conversations are retained as JSONL in:

- `.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`;
- `.codex/archived_sessions/rollout-*.jsonl`.

The scan found 1,536 rollout files, all with readable session metadata, totaling approximately
2.61 GB. No source rollout was modified. Observed JSONL row types included `session_meta`,
`event_msg`, `response_item`, `world_state`, and `turn_context`. They preserve session and turn IDs,
timestamps, user/assistant messages, tool calls and outputs, cwd, originator/source, Git remote,
branch, commit SHA, model/version data, and other execution metadata.

Two read-only SQLite stores provide indexes/projections:

- `state_5.sqlite`: `threads` includes rollout path, created/updated times, cwd, title, source,
  archive state, Git SHA/branch/origin, first user message, model, reasoning effort, thread source,
  originator, and related metadata.
- `thread_history_1.sqlite`: `thread_turns` maps thread/turn IDs to rollout ordinals and byte offsets;
  `thread_items` and `thread_realtime_items` contain typed item JSON and ordinals.

The JSONL rollouts were used as the raw evidence because they contain the complete ordered event
stream. SQLite was inspected for discoverability and schema corroboration, not mutated.

### Normalized conversation representation

`align_decisions.py` normalizes a rollout into turn blocks while preserving:

- session ID and session timestamp;
- turn number and turn ID;
- item timestamp, role, and message text;
- cwd and repository metadata from `session_meta`;
- source rollout path and JSONL ordinal.

User and assistant messages are retained verbatim only in the private audit. Tool events are reduced
to the tool name and path-like identifiers for matching; raw payloads, telemetry, system/developer
instructions, and routine internal metadata are excluded. The tracked review stores coordinates and
a SHA-256 of each bounded window instead of raw conversation text.

## 3. Alignment methodology

### Sampling

The 1,640 canonical decisions were sorted by decision ID, then 50 were sampled uniformly without
replacement with Python's seeded PRNG using seed `20260924`. The resulting ordered ID list has SHA-256
`80bdbc62598d1c207ec2173bd92ca65833105f0b9dfe9c0a25356142795cb52e`. The sample spans
2026-05-29 through 2026-09-19 and contains 23 Codex, 26 Claude, and 1 Claude Sonnet 4.6 records.

This method is reproducible and deliberately does not stratify or cherry-pick easy records. The full
sample IDs are in `results/alignments.json`.

### Candidate generation and scoring

Repository sessions were selected by normalized Git remote or by cwd containment within any
registered checkout/worktree for this repository. Derived guardian/approval sessions were excluded.
For each decision, candidate sessions had to:

- be actor-compatible with the recorded agent family;
- start within 72 hours before the decision timestamp, allowing two hours of positive clock drift;
- belong to this repository.

This left 917 repository rollouts overall, 171 rollouts relevant to at least one sampled decision,
and 297 normalized turn blocks after the temporal and actor filters.

The matcher uses a deterministic word/bigram TF-IDF cosine shortlist, then combines:

- lexical cosine;
- distinctive token overlap and longest shared phrase;
- filename/path/function/identifier overlap;
- temporal proximity;
- agent compatibility;
- branch and commit equality when available.

Each session contributes its strongest turn. The second-best result must come from a different
session. A returned window contains two turns before and two turns after the winning turn, bounded to
the same session. This fixed radius was chosen for reproducibility; it is not asserted to be the best
future windowing policy.

The confidence rules are intentionally conservative and are emitted with the result metadata:

- High: score at least 0.48, strong lexical/phrase evidence, and margin at least 0.06;
- Medium: score at least 0.34, cosine at least 0.14, and at least two supporting signal families;
- Low: score at least 0.22;
- No match: lower score or no candidate turn.

A second session is marked competitive if it scores at least 85% of the best result, or the margin is
below 0.06 while both remain plausible.

### Leakage controls learned during the experiment

Early instrument runs exposed false matches that looked excellent numerically but were not source
provenance. The final run therefore excludes:

- guardian/approval conversations that replay another agent's transcript;
- wrapper messages beginning with a copied Codex agent history;
- turns that already name the minted Memory Seed `entry_id`;
- full tool inputs, especially later session-append calls containing the finished decision text;
- materially later sessions, which are more likely to be retrieval or review than origin.

These controls materially lowered the apparent success rate. That reduction is a desirable result:
the experiment is meant to locate source windows, not merely later occurrences of the same wording.

## 4. Results

| Confidence | Count | Percent |
|---|---:|---:|
| High | 0 | 0% |
| Medium | 3 | 6% |
| Low | 10 | 20% |
| No match | 37 | 74% |

- Automatically aligned at High or Medium: **3/50 (6%)**.
- At least a weak candidate at Low or better: **13/50 (26%)**.
- Multiple plausible source sessions: **6/50 (12%)**.
- Codex-authored subset: **3 Medium, 10 Low, 10 No match out of 23**.
- Claude-family subset: **27 No match out of 27**, as expected under actor-compatible Codex-only
  source search.

The absence of High results reflects conservative margin requirements rather than failure of all
three useful matches. Manual inspection found all three Medium windows credible:

1. `mse_m6nrb8v2x05bv0hm:d1` aligned to session
   `019f0b5e-267a-7263-8c5c-0f6fb130fe4b`, turn 15. The window contains the user's request for
   fixed timeline granularity widths, the implementation discussion, matching frontend/test files,
   and verification that precedes the recorded decision.
2. `mse_wk3e5p73shz4edbb:d1` aligned to the same session, turn 8. The source discussion diagnoses the
   timeline scroll-height/grid constraint and implements the same CSS/test decision. This is a useful
   example of two different decisions arising from one long session.
3. `mse_z61np2tq3zkg01ew:d1` aligned to session
   `019f0a8c-6dfa-72f3-902a-fe8af9bcf875`, turn 6. The window contains the design-pack request,
   Radix/shadcn/Tremor/Untitled recommendation, and the user's acceptance.

The ten Low candidates should not be promoted to labels without owner audit. Six have competitive
alternative sessions; four are unique but have weak or rewritten evidence. The complete 50-row audit
is in `results/review.md`; raw windows are kept in the explicitly private local audit directory.

## 5. Failure analysis

The diagnostic categories for the 47 non-Medium rows were:

| Diagnostic category | Count | Interpretation |
|---|---:|---|
| Recorded outside retained Codex history | 27 | Claude-family decision; Codex is the wrong source store |
| No sufficiently similar candidate | 10 | Codex decision, but no plausible turn in the bounded set |
| Multiple conversations discuss similar material | 6 | Low-confidence result with competitive sessions |
| Rewritten/synthesized/weakly distinctive | 4 | Unique Low result but insufficient source evidence |

Observed and plausible failure mechanisms are:

- **Source coverage mismatch.** A random Memory Seed sample is cross-agent, while the inspected raw
  store is Codex-specific. This is the dominant failure mode.
- **No first-hand session link.** Existing decisions normally lack `session_id`, turn IDs, or source
  ordinals, forcing inference from weaker fields.
- **Decision wording was rewritten.** Structured D/R/F/T prose can be substantially more explicit
  than the conversational source.
- **Multi-turn synthesis.** A fixed five-turn window may miss reasoning distributed across a long
  conversation.
- **Repeated project vocabulary.** Common filenames and Memory Seed architecture terms recur across
  sessions, producing multiple plausible windows.
- **Timestamp limitations.** The record time is when memory was written, not necessarily when the
  underlying decision first emerged. A session-start prefilter can also exclude a long-running
  conversation that began more than 72 hours earlier.
- **Non-conversational origin.** Some decisions may be inferred from code changes, tests, web
  research, imported notes, or work performed outside Codex.
- **Retention gaps.** Old sessions may be absent, archived elsewhere, or associated with a different
  local agent store.
- **Leakage masquerading as provenance.** Later appends, retrievals, or approval replays can reproduce
  exact final wording. Without the final exclusions, these created false confidence.

Unknowns remain explicit: this experiment did not inspect Claude's raw storage, cannot prove that a
No-match source is deleted rather than merely elsewhere, and did not manually adjudicate all ten Low
rows.

## 6. Dataset feasibility

The process can generate useful examples, but only after provenance coverage improves.

### Positive examples

A positive should be a manually confirmed source span for a known decision, not just the
highest-scoring window. It should include enough local context to support the decision while avoiding
later text that copies the finished record. A practical first representation is the confirmed turn
plus two adjacent turns, with a second topic-contiguous representation retained for comparison.
Multiple decisions in the same session should remain separate labels but share a grouping key.

### Negative and unlabeled examples

Unlinked text is **unlabeled**, not negative: Memory Seed may have missed a decision. Safer initial
negative sources are:

- manually audited spans containing routine status, navigation, test output, or factual lookup with
  no commitment/change/selection;
- tool-only or telemetry-only spans after confirming no surrounding decision context;
- controlled conversations authored specifically as non-decision tasks;
- spans adjudicated independently by at least two reviewers, with disagreements retained as
  uncertain rather than forced negative.

Hard negatives should later include discussion of alternatives that ends without a decision, and
later retrieval/review of an already-made decision. Those are valuable but require careful labeling.

### Initial scale

An initial baseline likely needs roughly 500-1,000 manually confirmed positive windows plus two to
four times as many audited negatives/unlabeled examples to estimate high recall with useful
uncertainty bounds. This is an engineering estimate, not a result established by this 50-record
experiment. A smaller 100-200-positive pilot can validate labeling rules and window sizes but should
not be used to claim a 98% operating point.

### Leakage controls and evaluation split

Leakage risks include overlapping windows from the same conversation, multiple decisions from one
session, final decision prose copied into append calls, replayed transcripts, repeated worktree
threads, and near-identical project language.

The minimum split unit should be the entire source session. A stronger evaluation should reserve
whole projects as an out-of-domain test set after enough projects exist. All windows, decisions,
replays, and descendants of a session must remain in the same split. Threshold selection should use
a validation group, with the test group opened once. Report recall, false-negative rate, precision,
and fraction of conversation filtered out at each threshold.

### Optional classifier decision

No TF-IDF + logistic-regression classifier was trained. There are only three credible automatic
positives in this sample, the ten Low candidates are not yet trustworthy labels, and random text is
not a valid negative class. Training now would measure label leakage and sampling artifacts rather
than decision relevance.

## 7. Architecture implications

The experiment does not justify choosing the most elaborate architecture yet.

- **A — raw conversation -> curator:** remains the safe production fallback while detector recall is
  unmeasured, but it cannot repair missing provenance and retains the full processing cost.
- **B — deterministic high-recall detector -> curator:** is the best next experimental architecture.
  It can be evaluated with transparent cues and tuned for recall once first-hand positives exist.
- **C — lightweight classifier -> curator:** is not supported yet because trustworthy positive and
  negative labels are insufficient.
- **D — deterministic detector -> classifier -> curator:** remains a plausible eventual architecture,
  especially if rules cheaply reduce volume before a local classifier, but this experiment does not
  establish that the classifier adds value at the desired recall.

Therefore the evidence-based recommendation is **B for the next experiment, A as the current safety
baseline, and D only as a hypothesis to test after dataset construction**. The 98% target was not
tested: alignment coverage is not detector recall, and missing source sessions dominate the present
measurement.

## 8. Smallest next experiment

Collect 30 fresh Codex decisions prospectively. At decision-write time, capture first-hand provenance
for research purposes: session ID, deciding turn/span, cwd/project, timestamp, and whether the
decision was explicit or synthesized. Do not infer these links later.

Then, without exposing those gold spans to detector development:

1. run a deliberately broad deterministic cue detector over each complete session;
2. score whether every gold span is covered;
3. report decision recall, false-negative rate, precision, and candidate-volume reduction;
4. inspect every miss and adjust only on a development subset;
5. use the remaining sessions as a grouped holdout.

Thirty cases are enough to expose gross failures and labeling problems, though not enough to validate
98% recall statistically. This is the smallest experiment that separates provenance availability
from candidate-detection quality and most directly reduces the current uncertainty.

## Reproduction and outputs

Run from the repository root with a private output directory outside the repository:

```powershell
python -m unittest experiments/decision-chat-alignment/test_align_decisions.py
python -X utf8 experiments/decision-chat-alignment/align_decisions.py `
  --repo . `
  --output experiments/decision-chat-alignment/results `
  --private-output "$env:TEMP/memory-seed-decision-alignment-20260924"
```

Tracked outputs:

- `DESIGN-NOTE.md` — pre-registered design reasoning and experiment choices;
- `align_decisions.py` — read-only parser and matcher;
- `test_align_decisions.py` — parser, sampling, exclusion, and privacy checks;
- `results/alignments.json` — machine-readable 50-row result with sanitized source coordinates;
- `results/alignments.csv` — compact audit table;
- `results/review.md` — human-review form for all 50 decisions.

The raw-window JSON and Markdown audit are intentionally written only to the named private local
directory. They are not repository artifacts.
