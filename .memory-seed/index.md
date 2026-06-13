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
- Control-plane version: `2.6`.
- Package version: `2.6.0`.

## Topology

- Root routing files: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` (Copilot thin router).
- Runtime files: `.memory-seed/agent-rules.md`, `.memory-seed/project-bootstrap.md`, bootstrap-generated `.memory-seed/index.md`, bootstrap-generated `.memory-seed/policy.md`, init-managed `.memory-seed/project.yaml` (agent selection; written only on a subset), `.memory-seed/skills/`, `.memory-seed/sessions/`, `.memory-seed/archive/`, `.memory-seed/hooks/`.
- Lifecycle hooks (`.memory-seed/hooks/`): `session-log-check.py` (turn-end log reminder), `memory-retrieval-check.py` (per-prompt topical-retrieval reminder), `session-start-context.py` (SessionStart — injects the newest session entries so agents establish current state by recency, not semantic search). Per-agent events differ: Claude `Stop`/`UserPromptSubmit`/`SessionStart`; Codex same; Gemini `AfterAgent`/`BeforeAgent`/`SessionStart` (it has no `Stop`/`UserPromptSubmit`); Cursor `afterAgentResponse`/`sessionStart`.
- Agent hook configs (auto-merged by `init`/`update`): `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json`, `.cursor/hooks.json`, plus Copilot CLI `.github/hooks/memory-seed.json` (sessionStart prompt hook).
- Agent MCP configs (auto-registered by `init`/`update`): `.mcp.json` (Claude Code, project root), `.cursor/mcp.json` (Cursor), `.gemini/settings.json` (Gemini), `.codex/config.toml` (Codex, trusted directories only), `.github/mcp.json` (Copilot CLI, `mcpServers` key), `.vscode/mcp.json` (VS Code Copilot, `servers` key).
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
- Claude Code reads project-scope MCP servers from a project-root `.mcp.json`, NOT from `.claude/settings.json > mcpServers` (silently ignored). Versions 2.2.0–2.3.0 mis-wrote it to settings.json; `update` now writes `.mcp.json` and strips the dead block (ours-only).
- Codex reads project MCP from `.codex/config.toml` (`[mcp_servers.<name>]`, trusted directories only). Auto-registered via a zero-dependency TOML text-upsert (stdlib `tomllib` inspects; line-based writes preserve comments). A stale entry in a non-standard TOML form is left as a safe no-op.
- `doctor` has a non-fatal `warnings` channel (`DoctorResult.warnings`). It classifies the Codex MCP entry as absent/current/foreign/stale-fixable/stale-manual so an un-migratable stale entry is surfaced for manual fix rather than silently ignored.
- The single-decision DRAFT record is the **baseline** session-entry shape (since 2.4.0); the bare summary (simpler) and multi-decision (richer) shapes are explicit routes off it. D/R are mandatory, A/F/T optional.
- Release/publish: creating a GitHub Release triggers `.github/workflows/publish.yml`; the `pypi` environment has a **manual-approval gate** (a required reviewer must approve the deployment) before the OIDC PyPI push. The build job runs `tests.test_memory_seed`, so those tests must be clock-robust.
- Agent-selective install (Unreleased): `init` installs only the chosen agents' files; the set is persisted in `.memory-seed/project.yaml` (`agents:` list) and respected by `doctor`/`update`. Driven by the `KNOWN_AGENTS`/`_AGENT_MERGES`/`_AGENT_UNINSTALLS` registries in `core.py` and a per-`SeedFile` `agent` tag. **Absent project.yaml ⇒ ALL agents** (legacy/default unchanged); **present-but-empty `agents:` ⇒ zero agents** (distinct state). `agents add/remove` reconfigure; `remove` strips only our entries (foreign config preserved), never deletes shared dirs, backs up first. `codex`/`cursor` have no routing file (read `AGENTS.md` natively).

## Session Memory

- Append meaningful work notes to `.memory-seed/sessions/YYYY-MM-DD.md`.
- Keep session entries concise, publishable, and free of secrets.
- Older `.AGENTS/sessions/` logs were migrated into `.memory-seed/sessions/` for the v2 meta-test.
