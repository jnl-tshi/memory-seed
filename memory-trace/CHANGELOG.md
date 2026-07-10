# Changelog

All notable changes to Memory Trace are summarized here. Memory Trace depends on `memory-seed`
and consumes its public retrieval service; core behavior changes are recorded in the root
`CHANGELOG.md`.

## Unreleased

## 0.1.0 - unpublished (waiting on core memory-seed 2.17 on PyPI + PyPI project setup)

- First standalone distribution of the Memory Trace review UI, extracted from `memory-seed`
  (formerly Memory Lense; `memory-seed lense` remains as a deprecation shim in core).
- Read-only local browser UI over a project's Memory Seed runtime: search, filters, timeline,
  graph, Trail view (branch lineage + supersedes edges), reader/details with subsection
  highlighting, pane resizing, light/dark themes, accent palettes, and client-side Mermaid
  sidecar rendering with source fallback, backed by a rebuildable local SQLite cache outside the
  repository.
- Declares `memory-seed>=2.17` (requires the record-time `branch:` entry field the Trail view
  renders).
