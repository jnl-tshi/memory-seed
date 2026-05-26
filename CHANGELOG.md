# Changelog

All notable changes to Memory Seed are summarized here.

## Unreleased

- Added `.memory-seed/skills/index.md` as a deterministic skill trigger registry for universal lazy-loaded skills.
- Updated MCP memory retrieval to default to entry-level chunks using session YAML `entry_id`, with optional section granularity for narrower searches.
- Added control-plane guidance for sub-project runtime creation and parent/root coordination summaries without mirroring sub-project logs.
- Expanded operating-mode guidance for MCP history retrieval, unresolved history/current-file conflicts, public memory hygiene, and v2 guardrails.
- Clarified `uvx` one-off usage versus persistent `uv tool install`, project dependencies, and virtual-environment installs.

## 2.0.0 - 2026-05-25

- Promoted `.memory-seed/` as the canonical runtime directory with `agent-rules.md`, `project-bootstrap.md`, `index.md`, `policy.md`, lazy-loaded `skills/`, dated `sessions/`, and `archive/`.
- Added nearest-runtime discovery so nested sub-project folders can own isolated local memory state.
- Kept `.AGENTS/` as a code-level legacy fallback for older projects, but removed it from the v2 seed layout.
- Updated compact and MCP session extraction to use the discovered runtime boundary.
- Added default skill runbooks for security triage, data architecture, and local compilation.

## 1.6.1 - 2026-05-19

- Documented `uvx --from memory-seed` as the default way to run CLI and MCP commands without a global install.
- Clarified the difference between the Python package version and reusable control-plane version.
- Clarified that `memory-seed init` copies only Markdown seed files into target projects, not MCP server code or Python modules.

## 1.6.0 - 2026-05-19

- Added the local semantic cache core for heading-aware Markdown memory chunking, deterministic lexical ranking, optional embedding integration, and recency scoring.
- Added the lightweight stdio MCP server with `memory_search` and `memory_get_chunk` tools.
- Added `memory-seed-mcp-validate` for human-validatable search and fetch testing.
- Added support for timestamped session headings while keeping date-only session filenames.

## 1.5.3 - 2026-05-18

- Marked the project as beta maturity in package metadata.

## 1.5.2 - 2026-05-18

- Updated GitHub Actions workflow actions for Node.js 24 compatibility.

## 1.5.1 - 2026-05-18

- Prepared a patch release after the `1.5.0` PyPI release was already published.

## 1.5.0 - 2026-05-18

- Added the `memory-seed compact` command for summarizing recent session logs.
- Documented consolidation behavior and agent-led promotion of durable facts.

## Earlier

- Added reusable seed installation and update commands.
- Added project bootstrap instructions for generating `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and dated session logs.
- Added doctor/version checks for reusable control-plane files.
