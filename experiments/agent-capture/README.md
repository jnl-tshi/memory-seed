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
# 1. build the four templates for one agent (idempotent, deterministic)
python experiments/agent-capture/generate_fixtures.py --agent claude
python experiments/agent-capture/generate_fixtures.py --agent codex

# 2. one trial: level x task -> runs/<id>/ with transcript + readout
python experiments/agent-capture/run.py --level L0 --task T1 --agent claude

# 3. tabulate all runs, emit blind judge packets
python experiments/agent-capture/collect.py
```

Both agents are wired. Templates are per-agent (`templates/<agent>-<level>`), and the levels mean the
same thing on each: Codex reads `AGENTS.md` natively rather than a `CLAUDE.md` routing file, and keeps
its MCP registration in `.codex/config.toml` and its agent hooks in `.codex/hooks.json`. The Codex arm
needs several harness constants that Claude does not (project-trust injection, an approval bypass that
also covers MCP calls, and a tool-surface trim) — all of them, and why each is load-bearing, are in
the 2026-08-04 amendment to [PREREGISTRATION.md](PREREGISTRATION.md).

`run.py --brief "..."` substitutes the task brief for instrument probes. Those runs are marked
`brief_override` and `collect.py` drops them, so a probe can never land in a scored table.

## Invariants (violating any of these invalidates a run)

1. Sessions launch with **cwd = the run directory**, and the store must resolve inside the fixture
   (`resolve_runtime` walks upward with no boundary guard; H1/H4 in the plan). The Codex arm pins
   the MCP server's `cwd` explicitly per run rather than trusting inheritance; the Claude arm still
   relies on inheritance and that assumption is **unprobed** (see invariant 5).
2. Fixtures are their **own git repos** — the commit hook installs into the fixture's `.git`, and
   the parent's `prepare-commit-msg` glob can never stamp fixture entries onto parent commits.
3. Task briefs **never mention memory, recording, or documentation** — that signal is exactly the
   treatment being dosed.
4. Judge packets **never contain the answer key or the level label**.
5. Nothing here is scored until the smoke probes (one L0, one L3, unscored) have validated the
   instrument **for that agent**. As of 2026-08-04 Codex has passed both; **Claude has passed
   neither** — its probes were blocked on expired CLI auth, and both hazards the Codex probes turned
   up (MCP process cwd, an inherited account-level tool surface) have Claude analogues that are
   still unchecked. Passing on one agent validates nothing about the other; the open items are
   listed in the [PREREGISTRATION.md](PREREGISTRATION.md) amendment.
6. Every run fingerprints the parent's **session store** before and after and records
   `parent_isolated`. The Codex arm runs unsandboxed, so isolation is asserted per run, not
   assumed. Parent working-tree dirtiness is recorded alongside it but is informational only — the
   primary checkout is shared, so another session's edits are not this run's doing.
7. Results from different agents are **never pooled**. One capture-rate table per agent.

## Findings flow

Raw readouts stay in `runs/` (disposable). Scored results and their interpretation go to
`business/research/field-evidence-log.md` as a dated entry, with `runs/summary.json` attached.
Conclusions that survive belong in the wedge dossier — this directory only produces evidence.
