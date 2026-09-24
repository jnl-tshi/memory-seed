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
