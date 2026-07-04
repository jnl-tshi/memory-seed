---
memory-system-version: 2.15
tags:
  - memory-seed
  - proposal
  - agent-collaboration
  - worktrees
  - dependency-strategy
---

# Worktree Dependency Strategy Plan

> **Status: PROPOSED, not yet built.** Refined 2026-07-04 from the inbox proposal
> `memory-seed-worktree-dependency-control-plane-proposal.md`.

## Summary

Memory Seed should extend the existing Fan-Out Recipe with a vendor-neutral worktree and dependency
strategy. The change belongs in `agent_collaboration.md` and supporting roadmap docs, not in
always-read startup rules.

The durable rule:

```text
Worktrees isolate source edits.
Local environments isolate runtime state.
Shared caches reduce disk cost.
Dependency definition files are orchestrator-owned shared files.
```

This helps Codex, Claude, and other agents work in parallel without sharing a mutable source tree or
one live dependency environment.

## Priority

**P2 after the shipped collaboration recipe and graph metadata work.** The concept is important for
safe parallel work, but it should remain documentation-first until repeated manual use proves a need
for scaffolding.

Implementation order:

1. Add dependency tiers and task-packet fields to `agent_collaboration.md`.
2. Add a short tmux-as-optional-control-room note to `agent_collaboration.md`.
3. Add example task packets only after the core skill text is stable.
4. Consider a preview-only CLI scaffold only after manual use validates the workflow.

## Scope

### Phase 1 - Documentation Hardening

- Add a `Dependency Strategy` section to `.memory-seed/skills/agent_collaboration.md` and the seed
  twin.
- Define dependency tiers:
  - `none`: read-only work; no install required.
  - `isolated`: normal writing work; per-worktree environment.
  - `dependency-changing`: dependency definitions or lockfiles may change; orchestrator-owned
    integration and broader validation required.
- Extend the task-packet schema with:
  - `dependency_tier`
  - `dependency_setup`
  - `dependency_definition_policy`
  - `dependency_shared_cache_policy`
- Make dependency definition files and lockfiles explicit shared files:
  `pyproject.toml`, `requirements*.txt`, `uv.lock`, `package.json`, `package-lock.json`,
  `pnpm-lock.yaml`, and `yarn.lock`.
- Add the tmux note: tmux is optional operator convenience; Git branch/worktree state and task
  packets are the portable contract.

### Phase 2 - Examples

- Add example fanout task packets for:
  - docs-only work,
  - Python code work with a local `.venv`,
  - dependency-changing work.
- Keep examples in docs until the shape is stable enough for seed promotion.

### Phase 3 - Deferred Scaffold

Evaluate a preview-only command such as:

```text
memory-seed workflow fanout --topic <slug> --workers 2 --dry-run
```

The first scaffold must emit suggested artifacts only: task packets, branch names, worktree paths,
dependency tiers, validation checklist, review checklist, and cleanup checklist.

## Non-Goals

- Do not spawn agents.
- Do not require tmux.
- Do not create branches or worktrees automatically in the first increment.
- Do not mutate session logs from worker agents.
- Do not share one live virtual environment or installed dependency folder across parallel writing
  worktrees.
- Do not make `agent-rules.md` a worktree tutorial.

## Design Notes

Use the current collaboration boundary:

- The orchestrator owns task decomposition, branch/worktree naming, dependency-definition edits,
  integration order, final validation, and durable memory.
- Workers own bounded source edits and handoff evidence.
- Read-only explorers can share the current tree if they still verify `pwd`, repository root, `HEAD`,
  and relevant files before reporting.

Dependency-changing work is a coordination event. The orchestrator should decide whether to merge it
first, merge it last, or stop and rebase other worker branches before trusting their validation.

## Acceptance Criteria

- `agent_collaboration.md` and the seed twin contain the dependency strategy.
- The task-packet template contains the four dependency fields.
- The shared-file policy calls out dependency definition files and lockfiles.
- The tmux note is optional and clearly non-portable.
- Tests confirm live/seed parity and package inventory still pass.

