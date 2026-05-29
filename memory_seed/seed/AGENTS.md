---
memory-system-version: 2.1
tags:
  - agent-entry
  - ai-memory
---

# Agent Entry Point

This repository uses `.memory-seed/` as its agent memory and onboarding system.

Memory Seed is designed for file-reading AI coding agents. Keep the shared memory core in plain Markdown with predictable paths, explicit read order, and minimal vendor-specific assumptions. Tool-specific routing files should point into the nearest `.memory-seed/` runtime.

## Runtime Discovery

Before planning, editing, reviewing, or running commands, find the active runtime:

1. Start from the current working directory.
2. Walk upward toward the filesystem root.
3. Use the nearest ancestor that contains `.memory-seed/`.
4. If no `.memory-seed/` exists, fall back to legacy `.AGENTS/` only for older projects.

Nested sub-projects may have their own `.memory-seed/` directory. The nearest runtime owns active state and skills for work under that sub-project.

## Mode Check

Before choosing operating mode, check whether the active runtime contains:

```text
.memory-seed/agent-rules.md
.memory-seed/project-bootstrap.md
.memory-seed/skills/
.memory-seed/sessions/
.memory-seed/archive/
```

If these reusable control files exist but `.memory-seed/index.md` or `.memory-seed/policy.md` is missing, the project has been seeded but not bootstrapped. Use bootstrap mode to inspect the project, ask targeted questions, and generate those project-specific memory files.

If the reusable control files are missing, use bootstrap mode long enough to repair the runtime.

## Operating Mode

When initialized memory files exist, start here:

1. Read `.memory-seed/agent-rules.md` for operating-mode rules.
2. Read the active `.memory-seed/index.md` for topology, active state, and inheritance rules.
3. Read parent `.memory-seed/policy.md` only when the active index says policy is inherited.
4. Read the active `.memory-seed/policy.md` for behavioral constraints and local overrides.
5. Load files from `.memory-seed/skills/` only when the task matches a listed skill.

Do not read skills preemptively. Skills are lazy-loaded execution runbooks.

## Bootstrap Mode

When initializing or repairing a project, the seed installs the reusable control plane:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.memory-seed/
  agent-rules.md
  project-bootstrap.md
  skills/
  sessions/
  archive/
```

Bootstrap mode then generates `.memory-seed/index.md`, `.memory-seed/policy.md`, and the first dated session log after inspecting the project and asking any needed questions.

Sub-projects may define their own `.memory-seed/` directories inside their project folders. A sub-project runtime should keep active state local, use local skills by default, and inherit parent policy unless its `index.md` explicitly says otherwise.
