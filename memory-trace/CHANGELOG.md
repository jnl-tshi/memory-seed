# Changelog

All notable changes to Memory Trace are summarized here. Memory Trace ships inside
the main `memory-seed` distribution and consumes Memory Seed's public retrieval
service; core behavior changes are recorded in the root `CHANGELOG.md`.

## Unreleased

- Folded the planned standalone distribution back into the root `memory-seed`
  package. Install with `pip install "memory-seed[trace]"`; plain
  `pip install memory-seed` remains web-framework-free.

## 0.1.0 - bundled in memory-seed

- First bundled release of the Memory Trace review UI, extracted from the old
  in-package Memory Lense preview; `memory-seed lense` remains as a deprecation
  shim in core.
- Read-only local browser UI over a project's Memory Seed runtime: search, filters, timeline,
  graph, Trail view (branch lineage + supersedes edges), reader/details with subsection
  highlighting, pane resizing, light/dark themes, accent palettes, and client-side Mermaid
  sidecar rendering with source fallback, backed by a rebuildable local SQLite cache outside the
  repository.
- Requires the Memory Seed 2.17+ retrieval surface, including the record-time
  `branch:` entry field the Trail view renders.
