---
memory-system-version: 2.0
tags:
  - memory-seed
  - runtime-index
  - memory-seed-project
---

# Memory Seed Runtime Index

## Purpose

Memory Seed is a portable local memory system for AI coding agents. This runtime is the active control plane for developing the reusable seed, CLI, MCP memory retrieval, and compatibility behavior.

## Runtime Boundary

- Active runtime: nearest ancestor directory containing `.memory-seed/`.
- This repository root owns the root runtime.
- Nested sub-projects may define their own `.memory-seed/` directories inside their own folders.
- Legacy `.AGENTS/` remains supported by code for old projects, but this repository now uses the all-in-one `.memory-seed/` v2 layout.

## Inheritance

- Policy: inherit parent policy unless this file explicitly disables inheritance.
- Active state: local only.
- Skills: local only unless this file explicitly allows parent skill fallback.
- This root runtime has no parent runtime.

## Always Read

1. `AGENTS.md`
2. `.memory-seed/agent-rules.md`
3. `.memory-seed/index.md`
4. `.memory-seed/policy.md`
5. `.memory-seed/skills/index.md`

## Lazy Skills

Use `.memory-seed/skills/index.md` as the deterministic trigger registry. Load the full skill runbooks below only when the registry matches the task:

- `.memory-seed/skills/security_triage.md`
- `.memory-seed/skills/data_architecture.md`
- `.memory-seed/skills/local_compilation.md`
- `.memory-seed/skills/code_search.md`
- `.memory-seed/skills/memory_consolidation.md`
- `.memory-seed/skills/memory_doctor.md`
- `.memory-seed/skills/release_publishing.md`

## Active State

- Project type: reusable local AI memory-system seed and Python CLI/MCP tooling.
- Current priority: use this repository as a meta-test for the all-in-one `.memory-seed/` v2 layout with nearest-runtime sub-project discovery.
- Main output: plain-file local memory system for AI agents plus Python package `memory-seed`.
- Current risk: private/local system design work with possible personal notes because this project lives inside a second-brain folder.
- Control-plane version: `2.4`.
- Package version: `2.4.0`.

## Topology

- Root routing files: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`.
- Runtime files: `.memory-seed/agent-rules.md`, `.memory-seed/project-bootstrap.md`, bootstrap-generated `.memory-seed/index.md`, bootstrap-generated `.memory-seed/policy.md`, `.memory-seed/skills/`, `.memory-seed/sessions/`, `.memory-seed/archive/`, `.memory-seed/hooks/`.
- Agent hook configs: `.claude/settings.json` (Claude Code Stop hook), `.codex/hooks.json` (Codex CLI Stop hook) — both installed by `memory-seed init` via safe JSON merge.
- Legacy `.AGENTS/`: supported by code for old projects, but not part of the v2 target shape.
- Python orchestration: `memory_seed/core.py`, `memory_seed/semantic_cache.py`, `memory_seed/mcp_server.py`, `memory_seed/mcp_validate.py`, `memory_seed/cli.py`.
- Seed templates: `memory_seed/seed/`.
- Tests: `tests/`.
- Public docs: `README.md`, `CHANGELOG.md`, `NEXT_STEPS.md`.
- **Sub-project: `demo/`** — HyperFrames video composition (30 s product demo, MP4). Has its own `.memory-seed/` runtime; inherits root policy; does not use root AGENTS.md/CLAUDE.md (HyperFrames supplies those).

## Design Decisions

- `.memory-seed/` is the canonical runtime directory.
- Runtime discovery walks upward from `cwd` and uses the nearest `.memory-seed/`.
- `.memory-seed/agent-rules.md` and `.memory-seed/project-bootstrap.md` are reusable procedure files inside the runtime.
- `memory-seed init` installs reusable control files, generic skill templates, and lifecycle hooks; it does not create generated project memory files.
- `.claude/settings.json` and `.codex/hooks.json` are handled as JSON merge targets during init/update — not seed file copies — so existing agent config is preserved.
- `session-log-check.py` accepts `--codex` flag: outputs `hookSpecificOutput.additionalContext` for Claude, `systemMessage` for Codex.
- Bootstrap generates `index.md`, `policy.md`, and the first dated session log after inspecting the project and asking targeted user questions.
- Sub-projects live as normal folders with their own `.memory-seed/`; they are not nested inside the root `.memory-seed/`.
- Parent policy and skills are inherited by default for sub-projects unless the sub-project index records a local override; local skills should only duplicate parent skills when overriding behavior or defining genuinely local runbooks.
- `index.md` combines topology, active state, durable project context, current priorities, workflows, risks, inheritance, and skill activation.
- `policy.md` contains behavioral constraints only.
- `.memory-seed/skills/index.md` is the deterministic trigger registry for deciding which lazy-loaded skills apply.
- `skills/*.md` are lazy-loaded execution runbooks.
- `.memory-seed/sessions/` is the rationale and audit trail for decisions; `index.md` should store current orientation and durable conclusions, not full decision history.
- `memory-seed update` archives replaced reusable control-plane files under `.memory-seed/archive/<old-version>/` or `.memory-seed/archive/unknown-<timestamp>/` before refreshing them.
- MCP memory search uses the Model2Vec static embedding provider `model2vec:minishlab/potion-base-8M` by default and falls back to lexical, metadata, and recency ranking if semantic scoring fails or is disabled.

## Session Memory

- Append meaningful work notes to `.memory-seed/sessions/YYYY-MM-DD.md`.
- Keep session entries concise, publishable, and free of secrets.
- Older `.AGENTS/sessions/` logs were migrated into `.memory-seed/sessions/` for the v2 meta-test.
