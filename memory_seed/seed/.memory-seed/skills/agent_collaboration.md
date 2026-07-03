---
memory-system-version: 2.14
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
base_sha: "<commit hash the worker must verify before editing>"
working_branch: "<branch to write to, or read-only>"
worktree: "<path or 'current tree for read-only work'>"
expected_pwd: "<worktree path or repository root>"
objective: "<one concrete outcome>"
integration_artifact: "pr|merge-request|patch|branch|handoff"
capability_tier: "economy|standard|frontier"
shared_file_policy: "orchestrator_only"
conflict_owner: "<orchestrator|worker|human>"
allowed_files:
  - "<paths or globs the worker may edit>"
forbidden_files:
  - "<paths or globs the worker must not edit>"
preflight:
  - "pwd"
  - "git rev-parse --show-toplevel"
  - "git rev-parse HEAD"
  - "git status --short"
validation:
  - "<commands or checks to run>"
handoff_output:
  - "summary"
  - "files changed"
  - "commit hashes"
  - "tests run and result"
  - "known risks or conflicts"
conflict_escalation:
  - "<conditions requiring orchestrator or human review>"
review_loop:
  current_iteration: 0
  max_iterations: 2
  escalation: "<human-or-orchestrator>"
```

Keep packets narrow. Do not hand a worker the whole repository history when a path list, current plan, and a few relevant files are enough. Use capability tiers, never vendor or model names — providers change; roles and capability requirements are durable.

## Fan-Out Recipe: Explore / Plan / Implement / Validate

An optional Level 2/3 pattern for medium-to-large separable work — migrations, feature slices, broad test expansion, refactors with clear module boundaries. Not default behavior: the Scope Gate must state why direct (Level 0/1) work is insufficient. Avoid it for small fixes, tightly-coupled refactors where one coherent design matters more than speed, or work dominated by shared/control-plane files.

Gates, in order:

1. **Scope Gate.** Objective, non-goals, acceptance criteria, base branch/SHA, expected integration artifact, high-risk/shared files, and an explicit call on whether parallel implementation is justified (default: no, unless file ownership is clearly separable and the wall-clock reduction justifies the integration overhead).
2. **Exploration Gate.** Read-only agents, each given one narrow question, returning evidence — recommendations labeled as such, not stated as fact. Explorers may share the current tree since they never write, but that exemption covers write-collision safety only, not staleness: explorers still run the preflight commands and confirm their tree matches the intended base before their reads or citations are trusted.
3. **Plan Gate.** A single orchestrator reconciles explorer conflicts, chooses the architecture, assigns file ownership and interfaces, defines validation commands, and names the conflict owner. Use the strongest available capability tier here — same as review, not lighter. A weak plan poisons every downstream worker; review only catches what is already built.
4. **Worker Identity Gate.** Before a worker touches any file, it reports the packet's `preflight` output; the orchestrator verifies it matches the intended worktree and `base_sha` before the worker proceeds.
5. **Worktree Gate.** Parallel code-writing workers get separate worktrees, each with a bounded task packet. Workers never touch shared memory/session/control-plane files unless explicitly assigned — those stay orchestrator-owned per `shared_file_policy`.
6. **Pre-Review Validation Gate.** Each worker commits its own work and reports changed files, checks run, failures, skipped checks and why, and known risks *before* review. No uncommitted worker state gets integrated.
7. **Integration Gate.** The orchestrator merges worker branches one at a time into an integration branch, inspects the diff after each merge, resolves conflicts only via the named owner, and reruns targeted validation. No octopus merges for code.
8. **Bounded Review-to-Rework Loop.** An independent validator (same strong tier as planning) reviews the integrated diff against the plan. Findings route back to the Worktree Gate for revision, tracked by `review_loop.current_iteration` and capped at `max_iterations` (default 2) — then automation stops and produces a human decision summary. The loop must not restart exploration or planning automatically.
9. **Final Handoff Gate.** The orchestrator (never the workers) writes the integration artifact and the handoff session entry: base SHA, worker branches/worktrees, validation evidence, review result, unresolved risks. Workers' reported commit hashes belong in the handoff entry's records.

Capability tier guidance: exploration economy/standard; planning **frontier**; implementation standard; integration frontier or a senior orchestrator; review **frontier**. Planning and review both warrant the top tier — a weak plan is more expensive to catch later than a weak review.

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
