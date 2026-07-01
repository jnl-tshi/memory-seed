---
memory-system-version: 2.12
tags:
  - memory-seed
  - skill
  - agent-collaboration
---

# Agent Collaboration Skill

Use this skill for Git-first collaboration involving subagents, branch/worktree coordination, validator passes, merge-conflict handling, or multi-developer agent workflows.

## Principles

- Git-first collaboration: branches and worktrees isolate filesystem state; task packets isolate agent context; review and CI isolate integration risk.
- Follow the repository's existing branch naming convention first. If none exists, use `<owner>/<kind>/<topic>`, where `kind` is `feature|fix|refactor|test|docs`.
- Keep branches short-lived and focused on one coherent feature, fix, refactor, test change, or documentation change.
- Parallel code-writing agents use separate worktrees. Put plainly: parallel code-writing agents use separate worktrees. Read-only research, review, and validation agents may share the current tree.
- The orchestrator owns scope, sequencing, integration, final validation, and durable session logging for subagent work.
- Workers own bounded, non-overlapping file sets and report evidence instead of editing memory/session control files unless explicitly assigned.

## When To Use

Load this skill when the task involves any of:

- spawning or coordinating subagents
- assigning work across multiple humans using agents
- creating or reviewing feature branches
- using git worktrees to isolate parallel work
- preparing a worker or validator handoff
- resolving merge conflicts caused by agent or multi-developer edits
- deciding whether work should happen inline, on a branch, in a worktree, or through a pull request

## Collaboration Modes

### Single-Agent Branch Work

- Use when one agent implements one scoped change.
- Work on a branch unless the user explicitly asks to work directly on the current branch.
- Keep commits reviewable and run the smallest relevant validation before handoff.

### Orchestrated Subagents

- Use when splitting work reduces risk, wall-clock time, or context load.
- Orchestrator prepares Task Packet entries for each worker.
- Each code-writing worker gets a separate worktree unless the task is strictly sequential.
- Validators review from the integration branch or final diff, not from a worker's unmerged assumptions.

### Multi-Developer Agent Work

- Use per-developer branches and per-user session targets where configured.
- Prefer pull requests, protected integration branches, CI, and merge queues when the hosting provider supports them.
- Treat GitHub, GitLab, and similar PR systems as optional integration layers; the portable contract is Git branch, worktree, validation, and handoff evidence.

## Task Packet

Every worker packet should include:

```yaml
owner: "<human-or-agent-slug>"
role: "worker|validator|researcher"
base_branch: "<branch to start from>"
working_branch: "<branch to write to, or read-only>"
worktree: "<path or 'current tree for read-only work'>"
objective: "<one concrete outcome>"
allowed_files:
  - "<paths or globs the worker may edit>"
forbidden_files:
  - "<paths or globs the worker must not edit>"
validation:
  - "<commands or checks to run>"
handoff_output:
  - "summary"
  - "files changed"
  - "tests run and result"
  - "known risks or conflicts"
conflict_escalation:
  - "<conditions requiring orchestrator or human review>"
```

Keep packets narrow. Do not hand a worker the whole repository history when a path list, current plan, and a few relevant files are enough.

## Branch And Worktree Defaults

- Start from the current integration branch, normally `main`, unless the user or repository names another base.
- Update from the base branch before starting long-running work.
- Name branches by repository convention first; otherwise use `<owner>/<kind>/<topic>`.
- Use separate worktrees for parallel code-writing agents to prevent uncommitted file collisions.
- Do not create a worktree inside a tracked directory unless the worktree directory is ignored.
- Avoid stacking unrelated features in one branch. Commit or park completed work before starting the next feature.

## Conflict Escalation

Workers may resolve conflicts in files they clearly own for the task.

Escalate to the orchestrator or human for:

- shared control-plane files such as `AGENTS.md`, `.memory-seed/agent-rules.md`, `.memory-seed/policy.md`, or skill registry files
- session or memory files unless the worker was assigned that exact write
- seed templates under `memory_seed/seed/`
- generated artifacts where the source of truth is unclear
- binary files
- conflicts involving user-owned or foreign content
- conflicts where both sides changed behavior, not just nearby formatting

When a conflict is resolved, the handoff must state which side won, why, and what validation was rerun. Repeated mechanical conflicts may use Git's recorded-resolution tooling when the repository owner enables it, but never treat recorded resolution as approval.

## Memory And Session Policy

- For subagent work, the orchestrator owns durable session logging and summarizes worker results.
- Workers should return handoff evidence instead of writing session logs unless the orchestrator explicitly delegates memory updates.
- In multi-developer workflows, use per-user session targets when configured so human contributors avoid same-file session conflicts.
- Do not rewrite old session entries to resolve conflicts. Append a new clarification entry when needed.

## Integration Checklist

- Branch is based on the intended integration branch.
- Worker edited only allowed files.
- Forbidden files are untouched or explicitly approved.
- Validation commands ran and results are recorded.
- Merge conflicts are resolved by the right owner.
- Session/memory updates are appended by the orchestrator or the responsible human.
- Final integration branch or PR diff receives a validator pass before merge.

## Output

Return a concise handoff with:

- branch and worktree used
- files changed
- validation run
- conflicts encountered and resolution owner
- risks, follow-ups, or integration blockers
