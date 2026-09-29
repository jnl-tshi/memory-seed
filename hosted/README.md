# Hosted feasibility experiments

`hosted/` is deliberately outside the OSS `memory_seed` package. It may reuse semantic contracts, but it has
no import back-edge into the local runtime and is not included in wheels, sdists, or console scripts.

## P0.2 decision capture

The `capture/` package is an experimental, fail-closed adapter for validated Codex desktop JSONL rollouts.
It preserves source coordinates and accessible payloads in a disposable SQLite queue, handles completed-line
checkpoints, replay, rotation, leases, and pause/resume gaps, and emits inert decision drafts only.

Run targeted tests:

```powershell
python -m pytest tests/test_mcp_decision_mark.py tests/test_hosted_decision_capture.py tests/test_p02_corpus.py tests/test_decision_marking_control_plane.py experiments/decision-chat-alignment/test_align_decisions.py
```

Run the owner-local, synthetic-safe evaluation without printing raw evidence:

```powershell
python -m hosted.evaluation.run_p02 --codex-home "$env:USERPROFILE\.codex" --output hosted/evaluation/results
```

The live adapter accepts only the explicitly listed CLI versions in `capture/codex_rollout.py`. Unknown versions,
events before validated session metadata, and malformed shapes produce diagnostics or fail closed. It never attempts
to expose encrypted or hidden reasoning.

The optional spaCy dependency is isolated under `experiments/spacy/`. Without it, the parser reports the
deterministic rules-only backend. Neither backend can promote a draft; a curator must verify evidence, actor,
and atomicity.
