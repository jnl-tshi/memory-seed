---
tags:
  - ai-memory
  - memory-index
  - operating-mode
---

# Agent Memory Index

## Always Read

1. `AGENTS.md`
2. `.AGENTS/agent-rules.md`
3. `.AGENTS/index.md`
4. `.AGENTS/context.md`
5. `.AGENTS/style.md` when writing, editing, naming, documenting, or changing conventions

## Historical Memory

- `.AGENTS/sessions/*.md` contains append-only dated session logs.
- Read the most recent session entries when the user asks for continuity, recent changes, or memory-system evaluation.
- Do not rewrite prior session logs unless the user explicitly asks for repair, archival cleanup, or correction.

## Hot Facts

- Project name: Memory Seed.
- Project type: reusable local AI memory-system seed and refinement workspace.
- Current priority: evolve the portable seed, CLI tooling, and local MCP memory retrieval; operating memory is healthy.
- Main output: plain-file local memory system for AI agents (no vendor lock-in) + Python CLI/MCP tooling on PyPI (`memory-seed`).
- CLI commands: `init`, `update`, `compact`, `doctor`, `version`.
- MCP tooling: `memory-seed-mcp --stdio` exposes `memory_search` and `memory_get_chunk`; `memory-seed-mcp-validate` demonstrates search-then-fetch validation.
- Control-plane version: `1.4`. Package version: `1.5.3`.
- Current risk: private/local system design work with possible personal notes because this project lives inside a second-brain folder.
- Compatibility target: Codex, Claude Code, Gemini CLI, and other file-reading AI coding agents.
- Publishing: always use `gh release create` (not `gh workflow run`) to trigger PyPI publish.

## Key Pointers

- `.AGENTS/context.md` owns project purpose, state, architecture, portability goals, and durable design decisions.
- `memory_seed/semantic_cache.py` owns local session-memory chunking and ranking; `memory_seed/mcp_server.py` owns the MCP adapter.
- `.AGENTS/project-bootstrap.md` owns bootstrap-time project classification and style-profile selection for new target projects.
- `.AGENTS/style.md` owns conventions for this initialized Memory Seed project after bootstrap has generated it.
- `.AGENTS/agent-rules.md` owns the operating workflow and file permission model.
- `.AGENTS/project-bootstrap.md` is bootstrap-only and should not be used during normal operating mode.

## Bootstrap Boundary

This project is in operating mode when `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and `.AGENTS/sessions/` exist.

Do not read or apply `.AGENTS/project-bootstrap.md` during operating mode except when repairing an incomplete `.AGENTS` memory system or initializing a brand-new target project.
