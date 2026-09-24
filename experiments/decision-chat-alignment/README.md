# Decision-to-chat alignment experiment

This directory contains a bounded, read-only experiment for aligning structured Memory Seed
decisions with local Codex rollout windows. Start with `REPORT.md` for results and limitations.

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
