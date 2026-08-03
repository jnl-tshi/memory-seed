# Agent-capture experiment

Does an agent with the Memory Seed MCP write path **record its decisions unprompted** — and what is
the minimum scaffolding at which that becomes reliable? This directory is the instrument. The
question, metrics, thresholds, and kill condition are pre-registered in
[PREREGISTRATION.md](PREREGISTRATION.md); read that before running anything scored.

## How it works

Four fixture templates (`L0`–`L3`), each a **standalone git repo** containing a small stub project
(`strutil`) plus a complete Memory Seed install at one scaffolding level — generated from real
`init_project()` output with documented strips, never hand-assembled. A headless session is
launched **with cwd = the run directory**, so nearest-runtime discovery makes the run's own
`.memory-seed/sessions/` the readout: whatever the agent recorded is simply *there*, and the parent
repo's corpus is never touched.

```
stubs/        hand-written constants: index.md/policy.md (identical across levels, keeps
              bootstrap mode from firing), the L1 one-liner, the stub project
tasks/        frozen task briefs + tasks.json answer key (judges never see the key)
templates/    GENERATED, gitignored - run generate_fixtures.py to (re)build
runs/         GENERATED, gitignored - one directory per trial, the readout lives inside
```

## Usage

```bash
# 1. build the four templates (idempotent, deterministic)
python experiments/agent-capture/generate_fixtures.py

# 2. one trial: level x task -> runs/<id>/ with transcript + readout
python experiments/agent-capture/run.py --level L0 --task T1

# 3. tabulate all runs, emit blind judge packets
python experiments/agent-capture/collect.py
```

## Invariants (violating any of these invalidates a run)

1. Sessions launch with **cwd = the run directory** — the MCP server inherits it, and the store
   resolves inside the fixture (`resolve_runtime` walks upward; H1/H4 in the plan).
2. Fixtures are their **own git repos** — the commit hook installs into the fixture's `.git`, and
   the parent's `prepare-commit-msg` glob can never stamp fixture entries onto parent commits.
3. Task briefs **never mention memory, recording, or documentation** — that signal is exactly the
   treatment being dosed.
4. Judge packets **never contain the answer key or the level label**.
5. Nothing here is scored until the smoke probes (one L0, one L3, unscored) have validated the
   instrument and PREREGISTRATION.md is committed unchanged.

## Findings flow

Raw readouts stay in `runs/` (disposable). Scored results and their interpretation go to
`business/research/field-evidence-log.md` as a dated entry, with `runs/summary.json` attached.
Conclusions that survive belong in the wedge dossier — this directory only produces evidence.
