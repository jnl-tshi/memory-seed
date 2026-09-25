# Turn-aware Codex decision-to-chat alignment experiment

Date: 2026-09-24

## 1. Design discovery summary

This remains a bounded discovery experiment, not a Memory Seed architecture change. Generic atomic-fact
extraction is not justified as a mandatory stage: most facts are irrelevant, while the useful property is
decision-focused decomposition into choice, rationale, alternatives, constraints, evidence, consequences,
and relationships. Deterministic linguistic signals and a possible small binary classifier should therefore
identify candidate regions, deliberately over-detect, and leave semantic interpretation to the curator.

The target detector question remains: **does this conversation block contain material relevant to a
decision?** Evaluation should prioritize decision recall, false-negative rate, and candidate-volume
reduction; precision is secondary and overall accuracy is not the objective. Approximately 98% recall is an
exploratory target, not a production requirement. Every retained candidate needs source-session and
source-span provenance.

## 2. Data discovery

Memory Seed decisions are canonical Decision chunks parsed from `.memory-seed/sessions/**/*.md`. The
experiment uses decision identity, heading timestamp, agent type, branch, commit references, project path,
source references, title, and record text.

Codex history is stored as JSONL beneath the local active and archived session stores. Relevant records are:

- `session_meta`: session ID, timestamp, cwd, repository metadata, branch and commit;
- `event_msg/task_started`: turn ID, turn-start timestamp, and often `collaboration_mode_kind`;
- `turn_context`: a second collaboration-mode source;
- `response_item`: visible user/assistant messages, tool calls, and reasoning records.

Reasoning records may contain encrypted content plus a readable `summary` array of `summary_text` objects.
The experiment ignores encrypted content and raw reasoning content. Readable summaries are transient
ranking input only; serialized outputs retain counts, timestamps, ordinals, and SHA-256 provenance, never
the summary text.

## 3. Alignment methodology

The run reuses the exact 50-decision Codex-only cohort from the second pass rather than resampling the now
larger corpus:

- exact filter: case-insensitive `agent_type == "codex"`;
- original seed: `20260924`;
- fixed sample-ID SHA-256: `73b2dc2de7967859c9b138a6fbd56b9b10774a453bc5d3ba7b76c6c7795179a6`;
- sample IDs loaded from `results-codex-only/alignments.json`, with a hard failure if any ID is missing or
  the hash differs.

All 916 actor-compatible repository rollouts were parsed before temporal filtering. Each turn begins at its
`task_started` timestamp and ends at the next turn start; the final turn ends at its last timestamped event.
A decision timestamp denotes the half-open minute beginning at that time. The initial anchor is the turn
active at the decision time, then an intersecting decision-minute turn, nearest preceding turn, or nearest
following turn within the two-hour clock-drift allowance.

Within each eligible session, matching searches backward from the anchor. Candidates comprise the anchor,
the three strongest visible-text predecessors, all earlier Plan turns, and earlier turns with readable-summary
similarity. Other sessions remain independent candidates; source windows never span sessions. The review
window is the winning turn plus two turns before and after.

The base confidence score retains visible TF-IDF, token/phrase/identifier overlap, turn-level temporal
proximity, actor, branch, and commit evidence. Plan mode adds at most `0.03` when visible support also exists.
Readable summaries add at most `0.06` to ranking. Neither auxiliary signal can independently raise confidence:
High/Medium/Low/No-match still use visible evidence and the original confidence thresholds.

## 4. Results

| Confidence | Turn-aware pass | Prior Codex-only pass | Change |
|---|---:|---:|---:|
| High | 2 (4%) | 0 | +2 |
| Medium | 2 (4%) | 2 | 0 |
| Low | 18 (36%) | 21 | -3 |
| No match | 28 (56%) | 27 | +1 |

- Automatically aligned at High or Medium: **4/50 (8%)**, up from **2/50 (4%)**.
- At least a Low candidate: **22/50 (44%)**, down from **23/50 (46%)**.
- Multiple plausible source windows: **13/50 (26%)**, up from **12/50 (24%)**.
- Plan mode changed the winning candidate for 4 decisions; all four remained No-match.
- Readable summaries supported 25 winning candidates but changed no winner.
- No readable summary surfaced a winner outside the visible-text top three.

Manual audit found all four High/Medium windows plausible source alignments:

1. `ms-c0d56306:d1` (High) lands on the active implementation turn separating `uvx`, `uv tool
   install`, `uv add`, and `uv pip install`.
2. `mse_vexkm8da35zj856x:d1` (High) lands on the active turn implementing the approved rendered-UI
   debugging persona and skill changes.
3. `mse_mrrnd0wam54vjrpc:d2` (Medium) backtracks from anchor turn 7 to Plan turn 6, where DRAFTS,
   source keywords, and shared case normalization were settled.
4. `mse_yqgwc39y2edbj9w5:d1` (Medium) lands on the active recovery turn where the merge gate rejected
   fabricated branch provenance and the non-governing reference-document strategy was chosen.

The tracked JSON, CSV, and Markdown review contain all 50 decisions and candidate coordinates. The private
audit contains bounded visible-message windows only. Neither output contains encrypted reasoning, readable
summary text, or local user-profile paths.

## 5. Failure analysis

| Diagnostic category | Count |
|---|---:|
| No sufficiently similar turn in the temporal candidate set | 28 |
| Multiple conversations discuss similar material | 12 |
| Rewritten, synthesized, or weakly distinctive wording | 6 |
| Multiple plausible source windows despite Medium confidence | 1 |

Turn timestamps corrected two known matches from Medium to High and surfaced two additional Medium matches,
but did not reduce the No-match cases. The remaining failures are not primarily a session-start problem.
They reflect missing or deleted source history, decisions created outside retained Codex conversations,
substantial rewriting, repeated project vocabulary, long multi-turn synthesis, and records derived from code
or completed work rather than a single decision statement.

Ambiguity rose because parsing all repository sessions improved recall exposure: more genuinely competing
windows are now visible instead of being excluded by session-start time. This is a more honest instrument,
not evidence that the underlying provenance became worse.

Readable summaries did not alter any winning alignment. They can strengthen evidence for an already visible
candidate, but this run provides no evidence that they recover otherwise missed decisions. Plan mode helped
rank four candidates, but none crossed the Low threshold; Plan mode is useful context, not a source criterion.

## 6. Dataset feasibility

The aligned windows are useful as a seed for manual annotation, but not yet as classifier-ready labels. Only
four of fifty are manually plausible High/Medium positives, while Low and unlinked text remain unlabeled.
Memory Seed may itself have missed decisions, so unmatched conversation must not be treated as negative.

A positive example should be a manually verified source turn plus the smallest adjacent context needed to
recover the decision—normally the winning turn with up to two neighboring turns, or an earlier Plan turn and
its anchor when the decision was settled before implementation.

High-confidence negatives should come from manually reviewed blocks that perform clearly non-decision work,
such as mechanical test output, status-only tool traffic, or factual retrieval with no choice, rejection,
commitment, deferral, or change of direction. Random unlinked windows remain unlabeled. Hard negatives should
later include repeated vocabulary near real decisions, but only after human review.

An initial baseline should target roughly 200–500 manually verified positive windows and two to four times as
many reviewed negatives. Split by complete session, with a stricter project-level or time-based holdout where
possible. Never place overlapping windows, decisions from one session, or near-duplicate implementation turns
across train and test. Final Memory Seed decision wording must not be included as a model feature; it is label
construction evidence and would leak the target.

No classifier was trained because the retrospective labels remain too sparse and uncertain.

## 7. Architecture implications

- **A — raw conversation → curator:** remains the safe production fallback because no detector has yet
  demonstrated the required recall.
- **B — deterministic high-recall detector → curator:** is the best next experimental architecture. Turn
  timing, lexical signals, and optional Plan context are cheap, interpretable, and improved paired alignment,
  but recall and volume reduction still need prospective measurement.
- **C — lightweight classifier → curator:** is premature because trustworthy positive and negative labels do
  not yet exist.
- **D — deterministic detector → classifier → curator:** adds an unsupported second filter and therefore an
  additional false-negative boundary before either component has been validated.

The evidence supports testing B, not deploying it. A should remain the operational fallback until a detector
meets an agreed recall threshold on prospective gold spans. Readable reasoning summaries should remain an
optional tie-breaker rather than a required dependency.

## 8. Next experiment

Prospectively capture first-hand session ID, source turn ID, and bounded source span for the next 30 genuine
Codex decisions. Blindly run a deterministic over-detecting candidate detector over those sessions and report:

- decision recall and false-negative rate;
- candidate-volume reduction;
- precision as a secondary metric;
- recall with and without Plan and readable-summary signals.

This is the smallest experiment that tests the actual detector objective, produces defensible labels, and
shows whether B can reduce curator input without approaching the exploratory 98% recall boundary from below.

## Outputs

- `results-codex-turn-aware/alignments.json` — sanitized machine-readable results;
- `results-codex-turn-aware/alignments.csv` — compact audit table;
- `results-codex-turn-aware/review.md` — all 50 decisions and candidate coordinates;
- private visible-window audit — stored only in the explicitly named local temporary directory.

No Memory Seed decision record or Codex rollout was modified.
