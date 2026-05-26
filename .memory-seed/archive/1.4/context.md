---
tags:
  - ai-memory
  - project-context
  - memory-seed
---

# Project Context

## Purpose

Memory Seed is the refinement workspace for a portable local AI memory system. The system is designed to be dropped into new or existing projects so a project-specific memory can grow from a small seed of local Markdown files.

The goal is to preserve key project context, decisions, risks, workflow rules, and handoff notes across AI coding sessions without vendor lock-in.

## Fast Orientation

- Start at `AGENTS.md`.
- Follow `.AGENTS/agent-rules.md` for read order, file ownership, and session logging.
- Use `.AGENTS/index.md` as the compact memory map.
- Use this file for durable project context and current design decisions.
- Use `.AGENTS/style.md` for writing and documentation conventions in this initialized Memory Seed project.
- Use `.AGENTS/sessions/` for append-only chronological work history.

## Current State

The Memory Seed control plane is in version `1.4`. The Python package is at version `1.6.1`.

Recent durable implementation state:

- `memory_seed.semantic_cache` provides heading-aware local session-memory chunking and ranking.
- `memory_seed.mcp_server` provides a dependency-light stdio MCP adapter exposing `memory_search` and `memory_get_chunk`.
- `memory_seed.mcp_validate` provides a human-readable validation workflow that runs search, fetches the top chunk by `chunk_id`, and prints source evidence.
- Console entry points now include `memory-seed-mcp --stdio` and `memory-seed-mcp-validate`.
- Public docs recommend `uvx --from memory-seed ...` by default, pinned `uvx --from memory-seed==<version> ...` for repeatability, and installed CLI usage for offline or lower-latency workflows.

Existing reusable control-plane artifacts:

- `AGENTS.md`
- `CLAUDE.md`
- `.AGENTS/agent-rules.md`
- `.AGENTS/project-bootstrap.md`

Operating memory artifacts created during repair:

- `.AGENTS/index.md`
- `.AGENTS/context.md`
- `.AGENTS/style.md`
- `.AGENTS/sessions/2026-05-17.md`

## Project Type And Risk

- Project type: reusable local AI memory-system seed and design workspace.
- Intended use: develop, test, and refine memory-system logic that can be initialized inside other projects.
- Primary audience: the project owner and AI coding agents working in local project folders.
- Compatibility target: Codex, Claude Code, Gemini CLI, and other AI coding agents that can read local files.
- Risk level: private/local, with possible personal or project-sensitive notes.
- Security posture: local-first, plain-text, privacy-aware, no unnecessary vendor-specific dependencies.
- Primary outputs: Markdown memory files, reusable control-plane templates, Python CLI (`memory-seed` on PyPI), and session logs that explain design evolution.

## Agent Start Here

At session start:

1. Read `AGENTS.md`.
2. Read `.AGENTS/agent-rules.md`.
3. Read `.AGENTS/index.md`.
4. Read this file.
5. Read `.AGENTS/style.md` when writing or editing documentation, templates, naming conventions, or project rules.
6. Read recent `.AGENTS/sessions/*` only when historical detail is needed or the user asks for recent memory.

## Project Folder Structure

```text
memory seed/
  AGENTS.md                 # Agent entry point for tools that support AGENTS.md
  CLAUDE.md                 # Claude-specific pointer into AGENTS.md
  GEMINI.md                 # Gemini-specific pointer into AGENTS.md
  .AGENTS/
    agent-rules.md          # Operating workflow and file permission model
    project-bootstrap.md    # Bootstrap and repair guide; not normal operating read order
    index.md                # Compact memory index
    context.md              # Durable project context and current state
    style.md                # Memory Seed project conventions generated for this initialized project
    sessions/               # Append-only dated session logs
```

## Core Workflow

Memory Seed has two workflows:

1. Operating mode for this initialized project.
2. Bootstrap or repair mode for planting or restoring the memory system in another project.

In operating mode, agents use `AGENTS.md`, `.AGENTS/agent-rules.md`, `.AGENTS/index.md`, and `.AGENTS/context.md`. Bootstrap guidance is only used when initializing a brand-new target project or repairing an incomplete `.AGENTS` folder.

Project-type-aware style selection belongs to bootstrap, not to an already-generated `style.md`. A virgin target project will have only the reusable control-plane seed, so `.AGENTS/project-bootstrap.md` must inspect and classify the target project, choose a style profile, and generate that target project's `.AGENTS/style.md`.

## Key Outputs

- A reusable local memory-system seed.
- Plain Markdown control-plane files that can be copied or initialized into other projects.
- Project-specific operating files generated in each target project.
- Session logs that capture why the memory system changes over time.
- Python CLI (`memory-seed`) published on PyPI with commands: `init`, `update`, `compact`, `doctor`, `version`.
- MCP server tooling for agent-native local memory search.
- Public project support files: `CHANGELOG.md`, `NEXT_STEPS.md`, and `.github/ISSUE_TEMPLATE/`.

## Publishing Convention

- Publish to PyPI by creating a GitHub Release (e.g. `gh release create v1.5.0 --title "v1.5.0" --notes "..."`).
- The release triggers the `publish.yml` workflow, which runs tests, builds, and publishes via PyPI trusted publishing.
- Do not use `gh workflow run` directly — it produces an unlabelled run in the Actions UI.
- The package version in `pyproject.toml` and the git tag must match (e.g. `version = "1.5.0"` and tag `v1.5.0`).

## Current Design Direction

- Do not pursue an HTML frontend/dashboard as a core Memory Seed direction; it clutters the project's purpose.
- Semble (github.com/MinishLab/semble) is the recommended code search tool for target code projects. It is wired into `agent-rules.md` (Level 0/1 tool hierarchy) and `project-bootstrap.md` (auto-included in AGENTS.md for software/library projects). Do not build a Markdown-optimised variant; Memory Seed files are intentionally small.
- Optimize orchestration and compacting around Markdown memory files rather than code-function names or source-symbol indexes.
- `memory-seed compact` is implemented. It summarises recent session activity into a Markdown report that an agent reads to identify and promote durable facts. The CLI summarises; the agent judges. No automated writes to durable files.
- Local semantic-cache/MCP retrieval is implemented as an importable core plus MCP adapter, not as a ranking-changing replacement for `compact`.
- Preserve current ranking behavior on `main`; ranking experiments should happen on a separate branch and merge only when fixture tests show clear improvements.

## Portability And Vendor Lock-In

The memory system should work through plain local files and predictable paths. Tool-specific routing files are allowed, but they should point into the same `.AGENTS/` memory core rather than creating separate memories for each vendor.

Known routing targets:

- `AGENTS.md` for agents that recognize this convention.
- `CLAUDE.md` for Claude Code.
- `GEMINI.md` for Gemini CLI.
- MCP clients can use `memory-seed-mcp --stdio` for structured local memory retrieval.

The design should remain usable by other file-reading AI coding agents such as IDE agents, terminal agents, and open-source coding assistants.

## Versioning And Archive Policy

`memory-system-version` applies to reusable seed/control-plane artifacts, not to generated operating files.

Reusable artifacts include:

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.AGENTS/agent-rules.md`
- `.AGENTS/project-bootstrap.md`
- future initializer scripts or templates

Generated operating files include:

- `.AGENTS/index.md`
- `.AGENTS/context.md`
- `.AGENTS/style.md`
- `.AGENTS/sessions/YYYY-MM-DD.md`

Version policy:

- Minor improvements can move `1.0` to `1.1`.
- Major structure or compatibility changes can move `1.x` to `2.0`.
- Before replacing reusable versioned artifacts, archive the previous versions under `.AGENTS/archive/<version>/`.
- Do not archive generated operating files by version. Record their meaningful changes in `.AGENTS/sessions/`.

## Security And Privacy Notes

- Treat this repository as private/local unless the user says otherwise.
- Avoid adding secrets, tokens, account identifiers, or private third-party content to reusable templates.
- Keep project-specific personal notes in generated operating files and session logs, not in reusable seed templates.
- Prefer local files and transparent scripts over vendor-hosted memory features.
- Any future initializer should avoid destructive writes unless it has explicit confirmation or a dry-run mode.
- Bootstrap must generate target-specific `style.md` guidance from the target project's classification; do not rely on this Memory Seed project's generated `style.md` as the reusable style router.

## Memory Rules

- Keep `context.md` durable and concise.
- Keep `index.md` short and navigational.
- Keep this project's generated `style.md` focused on Memory Seed conventions.
- Keep sessions append-only and chronological.
- Prefer timestamped session entry headings (`## YYYY-MM-DD HH:MM - Short title`) while keeping session filenames date-only.
- Promote only stable, reusable facts from sessions into `context.md`.
- Do not edit locked control-plane files unless the user explicitly asks for workflow, bootstrap, routing, versioning, or memory-structure changes.
