# Solar Filaments Stack Benchmark — Experiment 001

This is the experiment-local harness for comparing eight Claude context stacks on
Kaggle's Solar Filament Segmentation Challenge 2026. Read `PREREGISTRATION.md`
before running anything. The benchmark is **DRAFT** until the owner accepts the
Kaggle rules, downloads the data, fills the freeze manifest, and changes its status
to `FROZEN`.

The local agent is the subject. Colab is only a replaceable compute worker. Agent
active time, Colab compute wait, end-to-end elapsed time, and treatment setup time
are separate interval sets; GPU duration never contributes to agent efficiency.

## Commands

```powershell
# Validate definitions and show freeze blockers
python experiments/stack-benchmark/solar-filaments-001/harness.py check

# Fingerprint downloaded competition data
python experiments/stack-benchmark/solar-filaments-001/harness.py freeze-data --data data

# Generate eight isolated arm templates from a frozen starter repository
python experiments/stack-benchmark/solar-filaments-001/harness.py generate --source <starter-repo>

# Package a versioned Colab job from one run workspace
python experiments/stack-benchmark/solar-filaments-001/harness.py package-job --run <run-dir> --config <training.json>

# Validate a returned job bundle, collect runs, and render marginal comparisons
python experiments/stack-benchmark/solar-filaments-001/harness.py validate-job --job <job-dir>
python experiments/stack-benchmark/solar-filaments-001/harness.py collect
python experiments/stack-benchmark/solar-filaments-001/harness.py report
```

`generate`, `package-job`, `collect`, and `report` refuse unless the benchmark is
frozen. `check`, schema validation, deterministic generation tests, and synthetic
negative controls remain available while draft.

## Durable versus generated artifacts

Committed: preregistration, manifest, prompts, hidden-question definitions, schemas,
harness code, Colab worker, and summarized reports. Gitignored: competition data,
generated arms, raw runs, model weights, Graphify graphs, Semble indexes, caches,
transcripts, and returned Colab job artifacts.
