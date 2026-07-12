# Memory Trace

Memory Trace is the companion **review UI** for
[Memory Seed](https://pypi.org/project/memory-seed/) — a local, read-only browser
view over a project's cross-agent decision memory (session logs, the decision
graph, timelines, and authored decision diagrams).

It is a separate UI/source package from the `memory-seed` control plane on purpose:

- **Core stays lightweight.** `pip install memory-seed` installs no web framework
  and no UI code — just the local-first, file-based control plane agents rely on.
- **The UI keeps a clear source boundary.** Visual work can evolve without being tangled into
  control-plane modules.

The 2026-07-11 release-strategy revision keeps that architecture boundary but folds public
installation into the main package extra:

```bash
pip install "memory-seed[trace]"
memory-trace
```

The separate `memory-trace` PyPI name is blocked as too similar to an existing project, and the
commercial strategy does not use the install layer as the monetisation boundary.

Memory Trace **depends on** `memory-seed` and consumes its public retrieval
service (`memory_seed.retrieval`). It never reimplements parsing, ranking, the
graph-edge contract, or diagram-sidecar reading — the same answers as MCP, one
canonical chunk model, one canonical ranking service.

## Planning

Next-generation product and architecture planning lives in the parent repository docs:

- `../docs/2_Todo/memory-trace-product-and-system-architecture-blueprint.md`
- `../docs/2_Todo/memory-trace-next-generation-implementation-roadmap.md`
- `../docs/3_Spec/memory-trace-trail-search-and-graph-ux.md`
- `../docs/3_Spec/memory-trace-derived-artifact-provenance-contract.md`

## Install

Target public install path after the packaging fold-in:

```bash
pip install "memory-seed[trace]"
```

Current source-checkout install path before that fold-in:

```bash
pip install ./memory-trace
```

The source-checkout form pulls `memory-seed` plus `fastapi`/`uvicorn` automatically. The public
release should move those web dependencies behind the root `trace` extra.

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

Memory Trace replaces the old "Memory Lense" preview. `memory-seed[lense]` should remain a
deprecated alias for `memory-seed[trace]` for one release window. The deprecated `memory-seed lense`
command should keep pointing users to the `memory-trace` command.
