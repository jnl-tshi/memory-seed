---
memory-system-version: 1.4
tags:
  - agent-entry
  - ai-memory
---

# Agent Entry Point

This repository uses `.AGENTS/` as its agent memory and onboarding system.

Memory Seed is designed for file-reading AI coding agents. Keep the shared memory core in plain Markdown with predictable paths, explicit read order, and minimal vendor-specific assumptions. Tool-specific routing files should point into the same `.AGENTS/` memory core.

## Mode Check

Before choosing operating mode, check whether all initialized memory files exist:

```text
.AGENTS/index.md
.AGENTS/context.md
.AGENTS/style.md
.AGENTS/sessions/
```

If all of these exist, use operating mode. If any are missing, use bootstrap mode long enough to create the missing initialized memory files.

## Operating Mode

When initialized memory files exist, start here:

1. Read `.AGENTS/agent-rules.md`.
2. Read `.AGENTS/index.md` for the compact memory index.
3. Read `.AGENTS/context.md` for project orientation and current state.
4. Follow the start-of-work and end-of-work routines in `.AGENTS/agent-rules.md`.

Do not read or apply `.AGENTS/project-bootstrap.md` during operating mode.

## Bootstrap Mode

Use `.AGENTS/project-bootstrap.md` when initializing a brand-new project or repairing a missing/incomplete `.AGENTS` memory system. The normal bootstrap seed state is:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.AGENTS/
  agent-rules.md
  project-bootstrap.md
```

If `.AGENTS/` is missing, partial, or still seed-only, use `.AGENTS/project-bootstrap.md` only long enough to restore the standard structure. Once `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and `.AGENTS/sessions/` exist, bootstrap mode is complete and future agents must use operating mode.
