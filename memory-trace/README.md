# Memory Trace

Memory Trace is the companion **review UI** for
[Memory Seed](https://pypi.org/project/memory-seed/) — a local, read-only browser
view over a project's cross-agent decision memory (session logs, the decision
graph, timelines, and authored decision diagrams).

It is a **separate distribution** from the `memory-seed` control plane on purpose:

- **Core stays lightweight.** `pip install memory-seed` installs no web framework
  and no UI code — just the local-first, file-based control plane agents rely on.
- **The UI iterates on its own cadence.** Visual work here never rides a core
  version bump, and never destabilizes the control plane.

Memory Trace **depends on** `memory-seed` and consumes its public retrieval
service (`memory_seed.retrieval`). It never reimplements parsing, ranking, the
graph-edge contract, or diagram-sidecar reading — the same answers as MCP, one
canonical chunk model, one canonical ranking service.

## Install

```bash
pip install memory-trace
```

This pulls `memory-seed` (plus `fastapi`/`uvicorn`) automatically.

## Use

From inside a Memory Seed project (a directory whose `.memory-seed/` runtime is
discoverable):

```bash
memory-trace
```

Serves the read-only UI on a local port and opens a browser. Nothing is ever
written back to your session files; every deep link targets a stable
`chunk_id` / `entry_id`.

Options: `--cwd`, `--host`, `--port`, `--no-open`, `--rebuild-cache`.

## Upgrade preparation

Memory Trace delegates the same safe process-management workflow as Memory Seed:

```bash
memory-trace processes
memory-trace processes --json
memory-trace shutdown --dry-run
memory-trace shutdown
memory-trace shutdown --yes
memory-trace upgrade --dry-run --manager uv
memory-trace upgrade --manager uv
memory-trace upgrade --yes --manager uv
```

Shutdown defaults to `No` unless confirmed or run with `--yes`. Matching is conservative: generic
`python`, `uv`, `uvx`, and `pipx` processes are stopped only when their executable path or command
line clearly belongs to `memory-trace`. `upgrade` supports `--manager uv`, `--manager pipx`, and
`--manager pip`.

## Migrating from `memory-seed[lense]`

Memory Trace replaces the in-package `memory-seed[lense]` extra (the "Memory
Lense" preview). The deprecated `memory-seed lense` command still works when
`memory-trace` is installed, but prints a notice pointing here — use the
`memory-trace` command instead.
