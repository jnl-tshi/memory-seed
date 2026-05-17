# Memory Seed

Memory Seed is a portable local memory system for AI coding agents.

It provides a small set of plain Markdown control-plane files that can be planted into a new or existing project. During bootstrap, the seed generates project-specific operating memory so future agent sessions can recover the project's purpose, current state, conventions, risks, and recent decisions without depending on vendor-hosted memory.

## Goals

- Keep project memory local, inspectable, and portable.
- Support file-reading AI coding agents through predictable Markdown files.
- Route tool-specific entry files into one shared `.AGENTS/` memory core.
- Generate project-specific `index.md`, `context.md`, `style.md`, and session logs during bootstrap.
- Archive reusable control-plane versions while keeping generated project memory outside version archives.

## Reusable Seed Files

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.AGENTS/
  agent-rules.md
  project-bootstrap.md
```

## Generated Per-Project Files

```text
.AGENTS/
  index.md
  context.md
  style.md
  sessions/
```

## Current Version

The current reusable control-plane version is `1.2`.

Archived reusable versions are stored under `.AGENTS/archive/<version>/`.

## Python CLI

Memory Seed includes a small Python CLI.

From this repository, run:

```powershell
python -m memory_seed.cli version
python -m memory_seed.cli doctor
python -m memory_seed.cli init --dry-run
```

The `init` command copies only the reusable seed files into the current folder:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.AGENTS/agent-rules.md
.AGENTS/project-bootstrap.md
```

It does not copy generated project memory such as `.AGENTS/context.md`, `.AGENTS/index.md`, `.AGENTS/style.md`, `.AGENTS/sessions/`, or `.AGENTS/archive/`.

Use `--dry-run` to preview without changing files. Use `--force` only when you intentionally want to back up and replace existing seed files.

## Publishing

This repository is configured for PyPI trusted publishing from GitHub Actions.

PyPI pending publisher settings should match:

```text
PyPI Project Name: memory-seed
Owner: jnl-tshi
Repository name: memory-seed
Workflow name: publish.yml
Environment name: pypi
```

The publish workflow lives at `.github/workflows/publish.yml`. It runs tests, builds the package with `uv build`, and publishes through PyPI's trusted publisher flow.
