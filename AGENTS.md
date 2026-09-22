---
memory-system-version: 2.22
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

When initialized memory files exist, complete all of the following before acting on the task in
the prompt - task size is not a reason to skip or truncate this list, and reading this file is the
routing step, not the destination: step 1 still has to happen, not just be reached.

1. Read `.memory-seed/agent-rules.md` for operating-mode rules.
2. Read `.memory-seed/skills/orientation.md` and apply the SessionStart hook's measured context route. If
   hook facts are absent, run `memory-seed situate`. Short latest-session files are read whole; long files
   are compressed by a read-only economy worker under the skill's source-linked summary contract.
3. Once the user's intent is known: Read `.memory-seed/skills/index.md` as the deterministic skill trigger registry and load only matching skills.
4. Read the active `.memory-seed/index.md` sections when the task depends on topology, authority,
   inheritance, active state, or project-wide priorities.
5. Read inherited and active `.memory-seed/policy.md` before writes or when behavioral constraints matter.
6. Read a declared ratified Constitution before consequential design, governance, or control-plane work.

Do not read skills preemptively. Skills are lazy-loaded execution runbooks.
Load full files from `.memory-seed/skills/` only when the trigger registry matches the task.

<!-- BEGIN context-mode -->
## Context Mode Routing

When Context Mode MCP tools are available, prefer `ctx_execute`, `ctx_execute_file`, or
`ctx_batch_execute` for analysis whose raw or unpredictable output would otherwise enter the model
context. Continue using normal `exec_command`, `apply_patch`, direct file editing, and dedicated tools
for short fixed output, mutations, tests that need direct interaction, or purpose-built capabilities.
Context Mode is an optional capture layer; it does not replace Memory Seed authority, startup, write,
validation, or session-log requirements. This repository intentionally does not enable Context Mode's
broad `PreToolUse` enforcement hook.
<!-- END context-mode -->

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
