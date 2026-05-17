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
