---
tags:
  - ai-memory
  - style-guide
  - memory-seed
---

# Memory Seed Project Style Guide

## Style Basis

- Project type: reusable local AI memory-system seed and refinement workspace.
- Intended use: initialize and evolve project-local memory across AI coding sessions.
- Risk level: private/local, with possible personal or project-sensitive notes.
- Why these conventions apply: this file guides work inside the Memory Seed refinement project. Bootstrap-time style selection for new target projects belongs in `.AGENTS/project-bootstrap.md`, because target projects do not have a generated `style.md` until bootstrap creates one.

## Global Conventions

- Prefer plain Markdown with predictable headings.
- Keep files concise and navigable.
- Use explicit paths and exact filenames.
- Separate durable facts from session history.
- Write for future agents that know nothing about the current conversation.
- Avoid vendor-specific assumptions except in routing files whose purpose is vendor adaptation.
- Do not include secrets, credentials, private account details, or unnecessary personal data in reusable templates.

## Memory-System Development Style

- Be precise about whether a file is reusable control plane or generated operating memory.
- Record design changes and rationale in `.AGENTS/sessions/YYYY-MM-DD.md`.
- Promote stable decisions into `.AGENTS/context.md`.
- Keep `.AGENTS/index.md` short.
- Treat version changes as deliberate design events, not incidental edits.
- Archive only reusable versioned artifacts when replacing a prior memory-system version.
- Keep local retrieval tooling dependency-light by default; optional semantic embedding support should remain adapter-based unless explicitly promoted to a required dependency.
- Preserve proven ranking behavior on `main`; test ranking changes on a branch with human-validatable fixture tests before merging.

## Bootstrap Style Generation

- Treat `.AGENTS/project-bootstrap.md` as the reusable source of style-profile selection for new target projects.
- When improving style-profile logic, update bootstrap and bump/archive the reusable control-plane version when the behavior materially changes.
- Keep this file focused on how to work in the Memory Seed project itself.
- Do not assume this generated `style.md` will exist in a virgin target project.

## File-Specific Guidance

### `index.md`

- Keep it short.
- Use it as a map, not a history.
- Include hot facts that prevent agents from loading stale files or following the wrong workflow.

### `context.md`

- Store durable facts, current state, purpose, structure, risks, and active design decisions.
- Update it only when leaving it stale would mislead future work.
- Do not use it for raw session notes.

### `style.md`

- Store conventions that should survive across sessions.
- In this project, describe Memory Seed development conventions.
- In target projects, generated `style.md` should be created by bootstrap from the target project's classification.
- Keep the guidance practical and short enough that agents will actually use it.

### `sessions/YYYY-MM-DD.md`

- Append concise entries for meaningful work.
- Prefer entry headings like `## YYYY-MM-DD HH:MM - Short title` when time is known; keep filenames date-only.
- Include decisions, files changed, validation results, and follow-up gaps.
- Do not log every command or temporary observation.
