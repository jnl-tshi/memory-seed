# Decision-to-chat alignment experiment

This directory contains a bounded, read-only experiment for aligning structured Memory Seed
decisions with local Codex rollout windows. Start with `REPORT-CODEX-LINEAGE-CAUSAL.md` for the
structural repair and causal controls, then `GOLD-SET-REPORT.md` for the manually adjudicated fixed
50-decision cohort and candidate-window findings. `WINDOW-STRATEGY-REPORT.md` measures the recall and
conversation reduction of fixed, backward, Plan-aware, continuation-aware, and parent-lineage windows.
`ORIGIN-PHASE-REPORT.md` checks the proposed user/agent timing priors and reviewer-detection signals
against the same gold cohort.

The matcher never edits Memory Seed records or Codex rollouts. Public results contain source
coordinates and hashes; raw conversation windows are written only to the explicitly supplied private
output directory.

```powershell
python -m unittest experiments/decision-chat-alignment/test_align_decisions.py
python -X utf8 experiments/decision-chat-alignment/align_decisions.py `
  --repo . `
  --output experiments/decision-chat-alignment/results `
  --private-output "$env:TEMP/memory-seed-decision-alignment-20260924"
```

To restrict the eligible decision population before sampling, pass an exact agent tag. The tracked
Codex-only follow-up used:

```powershell
python -X utf8 experiments/decision-chat-alignment/align_decisions.py `
  --repo . `
  --decision-agent codex `
  --sample-size 50 `
  --seed 20260924 `
  --output experiments/decision-chat-alignment/results-codex-only `
  --private-output "$env:TEMP/memory-seed-decision-alignment-codex-only-20260924"
```

The third pass reuses those exact 50 decision IDs, anchors on individual turn timestamps, searches
backward within each session, and uses Plan mode plus readable reasoning summaries as ranking-only
signals:

```powershell
python -X utf8 experiments/decision-chat-alignment/align_decisions.py `
  --repo . `
  --decision-agent codex `
  --sample-size 50 `
  --seed 20260924 `
  --sample-ids-from experiments/decision-chat-alignment/results-codex-only/alignments.json `
  --output experiments/decision-chat-alignment/results-codex-turn-aware `
  --private-output "$env:TEMP/memory-seed-decision-alignment-third-pass-private"
```

After assembling `GOLD-SET.jsonl`, reproduce the structural window ablation with:

```powershell
python -X utf8 experiments/decision-chat-alignment/evaluate_window_strategies.py `
  --repo . `
  --output experiments/decision-chat-alignment
```

The evaluator reads retained Codex logs but writes only aggregate counts and source coordinates to
`WINDOW-STRATEGY-RESULTS.json`, `WINDOW-STRATEGY-ROWS.csv`, and
`WINDOW-STRATEGY-REPORT.md`. It does not serialize raw chat or reasoning-summary text.

To reproduce the origin, timing, and reviewer-signal hypothesis check:

```powershell
python -X utf8 experiments/decision-chat-alignment/evaluate_origin_phase_hypotheses.py `
  --repo . `
  --output experiments/decision-chat-alignment
```

This evaluator verifies cited timestamps against their source JSONL coordinates and writes only
aggregate metrics plus decision/source coordinates. It does not serialize raw chat or encrypted
reasoning.

To reproduce the short-span ranking ablation inside the lineage-aware 20-turn lookback safety
envelope, first regenerate the window-strategy results using the preceding command, then run:

```powershell
python -X utf8 experiments/decision-chat-alignment/evaluate_ranked_decision_spans.py `
  --repo . `
  --output experiments/decision-chat-alignment
```

See `RANKED-SPAN-REPORT.md` for the results and limitations. The evaluator writes only counts and
source coordinates to `RANKED-SPAN-RESULTS.json`; it does not serialize conversation text.

## Strict 100-decision extension (provisional gold set complete)

`COHORT-100-REPORT.md` is the result and `COHORT-100-STATUS.md` is the execution record. The original 50 tagged records
contain 47 typed Decisions and three Documentation controls, so the frozen
seeded extension samples **53** unseen typed Codex Decisions to reach 100
strict decisions. Do not redraw the sample while comparing retrieval changes.
The development/held-out split and source coordinates are in
`cohort-100/verification-split.json`; held-out candidate coordinates and raw
review packets stay in the explicitly supplied private directory.

The private review workflow is: two independent source checks, exact ordinal
and timestamp validation, explicit adjudicator selections, and only then the
fail-closed gold assembler. An automatic candidate is a search hint, never a
positive label. Blank or unresolved reviews do not become negatives.
Both new-cohort splits have now been independently reviewed and explicitly
adjudicated; the held-out labels were opened only after the retrieval setting
was frozen. The final source-lineage audit found one development/held-out
overlap group, reported in the result rather than repaired after unsealing.

```powershell
$reviewDir = Join-Path $env:TEMP 'memory-seed-cohort100-verification'
python -X utf8 experiments/decision-chat-alignment/validate_review_progress.py `
  --packet (Join-Path $reviewDir 'verifier-a-development-reviewed.json') `
  --codex-home (Join-Path $env:USERPROFILE '.codex')
python -X utf8 experiments/decision-chat-alignment/adjudicate_extended_reviews.py `
  --verifier-a (Join-Path $reviewDir 'verifier-a-development-reviewed.json') `
  --verifier-b (Join-Path $reviewDir 'verifier-b-development-reviewed.json') `
  --selections experiments/decision-chat-alignment/cohort-100/adjudication-selections.json `
  --output (Join-Path $reviewDir 'development-adjudication-draft.json')
```

The development selection file now records an explicit disposition for every
development case. `assemble_extended_gold.py` rejects incomplete packets and checks
causal source ordinals, including raw tool outputs absent from normalized chat.
Keep held-out reviews sealed until settings are frozen, and reassess grouping
by *actual source session* once those coordinates are known.

Once all development rows are reviewed and adjudicated, assemble and evaluate
them without touching the held-out packet:

```powershell
python -X utf8 experiments/decision-chat-alignment/assemble_extended_gold.py `
  --split experiments/decision-chat-alignment/cohort-100/verification-split.json `
  --split-name development `
  --alignments experiments/decision-chat-alignment/cohort-100/alignments/alignments.json `
  --verifier-a (Join-Path $reviewDir 'verifier-a-development-reviewed.json') `
  --verifier-b (Join-Path $reviewDir 'verifier-b-development-reviewed.json') `
  --adjudication (Join-Path $reviewDir 'development-adjudication-draft.json') `
  --codex-home (Join-Path $env:USERPROFILE '.codex') `
  --output experiments/decision-chat-alignment/cohort-100/development-gold.jsonl
python -X utf8 experiments/decision-chat-alignment/evaluate_window_strategies.py `
  --repo . --gold experiments/decision-chat-alignment/cohort-100/development-gold.jsonl `
  --alignments experiments/decision-chat-alignment/cohort-100/alignments/alignments.json `
  --output experiments/decision-chat-alignment/cohort-100/development-evaluation
python -X utf8 experiments/decision-chat-alignment/evaluate_ranked_decision_spans.py `
  --repo . --gold experiments/decision-chat-alignment/cohort-100/development-gold.jsonl `
  --window-results experiments/decision-chat-alignment/cohort-100/development-evaluation/WINDOW-STRATEGY-RESULTS.json `
  --output experiments/decision-chat-alignment/cohort-100/development-evaluation
```

The new window output includes source-scope coordinates, so staged coverage
can be scored before the slower local-tokenizer pass. `iteration_gate.py`
checks measured, frozen-development iterations; it never chooses a retrieval
change or evaluates sealed labels on its own.

The development-selected fallback also checks neighboring sessions without a
repository-only filter. Its one-recent-plus-one-text session rule is frozen in
`cohort-100/frozen-retrieval-setting.json`. Reproduce the development-only
coverage and token measurements with `evaluate_nearby_session_fallback.py`
followed by `measure_fallback_tokens.py`; see each script's `--help` for the
exact read-only inputs and explicit output path. The "conditional" cost is a
gold-oracle calculation, not an automatic decision that the evidence is enough.
Held-out outputs are under `cohort-100/heldout-evaluation/`. The final
`measure_cited_messages.py` run takes the historical, development, and held-out
gold files together, excludes the three Documentation controls from strict
totals, and counts exact cited raw ordinals without saving transcript text.
`check_source_leakage.py` groups sources through parent-agent lineage and
intentionally returns nonzero when the split overlaps.

For the original 50, `evaluate_staged_retrieval.py` measures the requested read
order using frozen window/ranker outputs: top three short spans **inside** the
20-turn lineage envelope, then the full envelope, then source-lineage
expansion. It reports an oracle stage from gold citations, not an automatic
semantic sufficiency detector. Token measurement uses a caller-supplied local
`tokenizer.json` and reports whole logical session, envelope, ranked spans,
and adjudicated useful content as **proxy tokens**, not Codex billing tokens.

```powershell
python -X utf8 experiments/decision-chat-alignment/evaluate_staged_retrieval.py `
  --gold experiments/decision-chat-alignment/GOLD-SET.jsonl `
  --window-results experiments/decision-chat-alignment/WINDOW-STRATEGY-RESULTS.json `
  --ranked-results experiments/decision-chat-alignment/RANKED-SPAN-RESULTS.json `
  --token-results experiments/decision-chat-alignment/TOKEN-EFFICIENCY-RESULTS.json `
  --cohort-manifest experiments/decision-chat-alignment/cohort-100/manifest.json `
  --output experiments/decision-chat-alignment/STAGED-RETRIEVAL-RESULTS.json
```
