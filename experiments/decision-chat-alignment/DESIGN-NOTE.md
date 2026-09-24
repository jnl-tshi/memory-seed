# Decision-to-chat alignment discovery

Status: bounded empirical experiment; no production architecture change.

## Question

Can existing Memory Seed decision records be aligned automatically to the bounded raw Codex
conversation windows from which they likely originated?

## Working architecture under investigation

```text
raw conversation
-> high-recall decision-candidate detection
-> optional lightweight decision/non-decision classifier
-> curator semantic interpretation
-> structured Memory Seed decision
```

The detector's job is only to say that something decision-like may be happening nearby. It must
optimize for recall, deliberately over-detect, and leave implicit decisions, multi-turn reasoning,
alternatives, rationale, supersession, ambiguity, and final decision boundaries to the curator.

## Settled discovery conclusions

1. Generic atomic-fact extraction is not a required pipeline stage. Extracting every fact and then
   reconstructing decisions would add compute and complexity while most facts are irrelevant.
2. The useful lesson from atomic extraction is decomposition. The desired atomic structures are
   decision-focused: what was decided, why, alternatives, constraints, evidence, consequences, and
   relationships to earlier decisions.
3. Deterministic linguistic extraction may be useful primarily as a candidate detector. Signals
   include choosing, preferring, replacing, rejecting, changing direction, committing to an
   implementation, settling an architecture, deferring work, and deciding not to act.
4. The deterministic layer should deliberately over-detect. Its output is a candidate span, not a
   final interpretation.
5. A small binary classifier may be useful after or instead of rules: decision-relevant block versus
   non-decision-relevant block.
6. Such a classifier may run locally at negligible marginal cost compared with an LLM classifier.
7. Primary evaluation metrics are decision recall, false-negative rate, and candidate-volume
   reduction. Precision is secondary; overall accuracy is not the target metric.
8. Approximately 98% known-decision recall is an exploratory operating target, not a production
   threshold.
9. The curator remains responsible for semantic interpretation.
10. Every aligned decision must retain source-session and source-span provenance.

## Pre-registered experiment choices

- Population: every parseable Memory Seed session record whose canonical chunk is a Decision (not a
  Documentation record) and has an `entry_id`.
- Sample: 50 records sampled uniformly without replacement after sorting by canonical decision ID.
- Random seed: `20260924`.
- Codex source: local rollout JSONL files beneath the active and archived Codex session stores.
- Repository membership: matching normalized Git remote, or a working directory at/under the target
  repository. Exact-root matching is not sufficient because agent worktrees live elsewhere.
- Time interpretation: Memory Seed heading timestamps are local Europe/London time; rollout timestamps
  are normalized to UTC. Candidate sessions start in the 72 hours before the decision timestamp, with
  at most two hours of positive clock drift. Materially later sessions are post-hoc discussion.
- Text representation: user and assistant message text, plus tool-call names and path-like identifiers.
  Developer/system instructions, guardian transcripts, approval-history wrappers, raw tool payloads,
  and turns already naming the final decision ID are excluded to prevent provenance leakage.
- Candidate unit: one turn block. The returned review window is the winning turn plus two turns before
  and two turns after, bounded to the same session.
- Matcher: deterministic word/bigram TF-IDF cosine plus token overlap, longest shared token phrase,
  identifier/file overlap, temporal proximity, actor compatibility, branch match, and commit match.
- Second-best candidate: the best-scoring turn from a different session.
- Multiple-plausible flag: second-best score at least 85% of the best, or score margin below 0.06 while
  the second candidate remains plausible.
- Confidence is rule-based and interpretable. Thresholds live in the script and are emitted in the
  result metadata; they are not ground-truth labels.

## Safety and provenance

The source rollout files are read-only. The parser records their absolute path, session ID, JSONL
ordinal, turn number, timestamps, cwd, repository metadata, and bounded message window. Raw conversation
text is owner-only evidence and is therefore emitted only to explicitly named private local outputs.
Tracked experiment results contain hashes and source coordinates rather than raw chat excerpts.

## Invalidation conditions

The experiment does not justify a detector architecture if the confidence categories fail manual
audit, if source windows are routinely missing, if the random sample is dominated by non-Codex
records, or if the matcher succeeds mainly through final decision wording copied verbatim into the
conversation. Any recommendation must distinguish those failure modes.
