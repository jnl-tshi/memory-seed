# Memory Trace

Memory Trace is the companion **review UI** for
[Memory Seed](https://pypi.org/project/memory-seed/) — a local, read-only browser
view over a project's cross-agent decision memory (session logs, the decision
graph, timelines, and authored decision diagrams). The Trail view is a
git-graph-style timeline: branch lanes from recorded `branch:` metadata,
commit-accurate fork/merge connectors driven by `Memory-Entry:` commit trailers
(positional "estimated" fallback for pre-trailer history), clickable trunk
merge rings, typed `replaces`/`evolves` lifecycle routes, and an on-device
worktree switcher for per-branch memory. The maintained React client consumes
the versioned `/api/v1/*` contract; unversioned `/api/*` routes remain only
as compatibility surfaces.

It is bundled into the main `memory-seed` distribution on purpose:

- **Core stays lightweight.** `pip install memory-seed` installs no web runtime
  dependencies: just the local-first, file-based control plane agents rely on.
- **One product, optional UI.** `pip install "memory-seed[trace]"` adds the
  FastAPI/Uvicorn runtime and installs the `memory-trace` command without
  requiring a separate PyPI project.

Memory Trace consumes Memory Seed's public retrieval service
(`memory_seed.retrieval`). It never reimplements parsing, ranking, the
graph-edge contract, or diagram-sidecar reading — the same answers as MCP, one
canonical chunk model, one canonical ranking service.

## Planning

Next-generation product and architecture planning lives in the parent repository docs:

- `../docs/2_Todo/memory-trace-product-and-system-architecture-blueprint.md`
- `../docs/2_Todo/memory-trace-next-generation-implementation-roadmap.md`
- `../docs/3_Spec/memory-trace-trail-search-and-graph-ux.md`
- `../docs/3_Spec/memory-trace-derived-artifact-provenance-contract.md`

## Install

Install the optional UI extra from the main package:

```bash
pip install "memory-seed[trace]"
```

Plain `pip install memory-seed` still installs the CLI, MCP server, and control
plane without the web stack. The deprecated `memory-seed[lense]` extra is kept
as a temporary alias for `memory-seed[trace]`.

## Use

From inside a Memory Seed project (a directory whose `.memory-seed/` runtime is
discoverable):

```bash
memory-trace
```

Serves the read-only UI on a local port and opens a browser. Nothing is ever
written back to your session files; every deep link targets a stable
`chunk_id` / `entry_id`.

The React UI is served at `/`; old `/next` bookmarks redirect there. Options:
`--cwd`, `--host`, `--port`, `--no-open`, `--rebuild-cache`, and `--static-root`
(serve a React build from another directory or checkout root - e.g. verify a git worktree's UI
without copying files; also settable as `MEMORY_TRACE_STATIC_ROOT`). Vite's content-addressed
asset names prevent stale browser bundles.

The external-project folder picker is available only when Trace is bound to a loopback host
(`127.0.0.1`, `::1`, or `localhost`). It reads the server filesystem, so `/api/v1/browse` and
`/api/v1/projects` return `403` when Trace is bound to a network-facing host.

## Frontend development

`/` serves the packaged React and TypeScript workspace shell. It consumes
only the versioned `/api/v1/*` contract and lazy-loads Cytoscape.js for the
Graph workspace. The former vanilla fallback was retired after product-owner
sign-off on 2026-08-11.

Build the preview assets before package validation:

```bash
cd memory-trace/client
npm ci
npm run build
```

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
`--manager pip`, but upgrades the owning `memory-seed` package because `memory-trace` is a bundled
command, not a separately published distribution.

## Migrating from `memory-seed[lense]`

Memory Trace replaces the old `memory-seed lense` preview command. The
deprecated `memory-seed lense` command still works when `memory-seed[trace]` is
installed, but prints a notice pointing here: use the `memory-trace` command
instead.
