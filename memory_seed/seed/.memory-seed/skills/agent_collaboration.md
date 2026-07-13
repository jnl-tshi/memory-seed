---
memory-system-version: 2.18
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
agent_type: "codex|claude|gemini|cursor|other"
role: "worker|validator|researcher"
base_branch: "<branch to start from>"
base_sha: "<commit hash the worker must verify before editing>"
working_branch: "<branch to write to, or read-only>"
worktree_namespace: ".codex/worktrees|.claude/worktrees|.gemini/worktrees|.cursor/worktrees|custom"
worktree: "<path or 'current tree for read-only work'>"
expected_pwd: "<worktree path or repository root>"
objective: "<one concrete outcome>"
integration_artifact: "pr|merge-request|patch|branch|handoff"
capability_tier: "economy|standard|frontier"
shared_file_policy: "orchestrator_only"
dependency_tier: "none|isolated|dependency-changing"
dependency_setup: "<none|per-worktree env command|orchestrator-coordinated>"
dependency_definition_policy: "orchestrator_only"
dependency_shared_cache_policy: "<shared read-only cache path, or 'none'>"
conflict_owner: "<orchestrator|worker|human>"
allowed_files:
  - "<paths or globs the worker may edit>"
forbidden_files:
  - "<paths or globs the worker must not edit>"
preflight:
  - "memory-seed worktree guard --agent <agent_type> --write-intent"
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
4. **Worker Identity Gate.** Before a worker touches any file, it reports the packet's `preflight` output; the orchestrator verifies `memory-seed worktree guard --agent <agent_type> --write-intent` passes, then verifies the intended worktree and `base_sha` before the worker proceeds.
5. **Worktree Gate.** Parallel code-writing workers get separate worktrees, each with a bounded task packet. Workers never touch shared memory/session/control-plane files unless explicitly assigned — those stay orchestrator-owned per `shared_file_policy`.
6. **Pre-Review Validation Gate.** Each worker commits its own work and reports changed files, checks run, failures, skipped checks and why, and known risks *before* review. No uncommitted worker state gets integrated.
7. **Integration Gate.** The orchestrator merges worker branches one at a time into an integration branch, inspects the diff after each merge, resolves conflicts only via the named owner, and reruns targeted validation. No octopus merges for code. When branch-local session entries or diagram sidecars exist, integrate that branch with `memory-seed session merge-branch --branch <branch>` — it dry-runs the fuse, performs the `--no-ff` merge, applies the fuse, and commits in one gated step. The lower-level `session fuse` dry-run/`--apply` pair remains available for manually inspected merges.
8. **Bounded Review-to-Rework Loop.** An independent validator (same strong tier as planning) reviews the integrated diff against the plan. Findings route back to the Worktree Gate for revision, tracked by `review_loop.current_iteration` and capped at `max_iterations` (default 2) — then automation stops and produces a human decision summary. The loop must not restart exploration or planning automatically.
9. **Final Handoff Gate.** The orchestrator (never the workers) writes the integration artifact and the handoff session entry: base SHA, worker branches/worktrees, validation evidence, review result, unresolved risks. Workers' reported commit hashes belong in the handoff entry's records. Set the entry's optional `branch:` field (see `session_logging.md`) from the Task Packet's `working_branch` — a durable record-time label, not a worktree path.

Capability tier guidance: exploration economy/standard; planning **frontier**; implementation standard; integration frontier or a senior orchestrator; review **frontier**. Planning and review both warrant the top tier — a weak plan is more expensive to catch later than a weak review.

## Branch And Worktree Defaults

- Start from the current integration branch, normally `main`, unless the user or repository names another base.
- Update from the base branch before starting long-running work.
- Name branches by repository convention first; otherwise use `<owner>/<kind>/<topic>`.
- Use separate worktrees for parallel code-writing agents to prevent uncommitted file collisions.
- Writing agents use their own namespace by default: Codex in `.codex/worktrees/<task>`, Claude in `.claude/worktrees/<task>`, Gemini in `.gemini/worktrees/<task>`, and Cursor in `.cursor/worktrees/<task>`. Configured third-party agents need an explicit namespace in `.memory-seed/project.yaml` before routine write work.
- Before editing in a branch/worktree workflow, run `memory-seed worktree guard --agent <agent> --write-intent`. A foreign namespace is a shared-control-plane STOP hazard; move to the correct worktree unless the user explicitly approves a different path.
- Root checkout is for read-only inspection, mainline integration, and approved cleanup. Routine feature edits should use an agent-owned task worktree; root writes require an explicit guard override (`--allow-root-write`) and should be recorded in the handoff.
- Do not create a worktree inside a tracked directory unless the worktree directory is ignored.
- Avoid stacking unrelated features in one branch. Commit or park completed work before starting the next feature.

## Branch History Preservation

Use this when the user expects Git history to show discrete feature branches and merges, or when
multiple writing agents work on different features at the same time.

- A worktree only isolates the working directory; it does not by itself create a visible branch in
  the Git graph. Visible topology requires commits on a task branch plus an integration merge commit.
- Distinct feature, proposal-implementation, fix, refactor, test, or documentation tasks should use
  their own task branch unless the user explicitly chooses direct `main` work for that task.
- Parallel writing agents get one task branch and one worktree each. Read-only researchers,
  reviewers, and validators may share the current tree because they do not write commits.
- Integrate completed task branches one at a time with `git merge --no-ff <branch>` when the desired
  outcome is a visible branch-and-merge graph. Avoid squash, rebase, or fast-forward integration when
  preserving branch shape matters. When the branch carries session entries or diagram sidecars,
  prefer `memory-seed session merge-branch --branch <branch>`, which performs the same `--no-ff`
  merge and fuses the session memory in one step.
- Do not delete task branches before the final handoff if the user wants the branch labels visible in
  local tools. If branches are later deleted, merge commits still preserve topology, but branch labels
  disappear.
- Before feature work starts, run `memory-seed branch status` when available. Treat warnings as a
  prompt to create or switch to a task branch, not as a hard block.
- To promote branch-local memory, run `memory-seed session merge-branch --branch <branch>` from the
  integration tree: it dry-runs the fuse, merges with `--no-ff`, applies the fuse, and commits —
  failing closed (fuse issues abort before the merge starts; non-session conflicts leave the merge
  in progress for the named conflict owner). The merge commit is stamped automatically with one
  `Memory-Entry: <entry_id>` trailer per fused entry (below git's prepared merge message), so
  `link commits` and trailer scans resolve fused entries to their integration point with no manual
  step. For a manually inspected merge, the lower-level
  `session fuse --branch <branch>` dry-run remains available; its `--apply` requires an in-progress
  `git merge --no-ff --no-commit <branch>`.
- Final handoff records the base SHA, task branch, worktree path, merge method (`--no-ff` when used),
  merge commit if available, validation, and unresolved risks.

## MCP Control Surface

When the Memory Seed MCP server is available, use it as the read-oriented coordination surface before
falling back to shell commands:

- `memory_branch_status` replaces the read-only CLI posture check for agents that can call MCP. Use
  it before distinct feature work, before assigning branch/worktree packets, and before explaining
  why a task should move off `main`.
- `memory_worktree_guard` mirrors `memory-seed worktree guard` as a read-only structured pre-write
  check. Use it before file edits when MCP is available; treat `safe_to_write: false` or
  `severity: block` as a blocker until the worker moves to the correct namespace or the user grants
  an explicit root-write override.
- `memory_session_fuse_preview` replaces the dry-run CLI preview for agents that can call MCP. Use it
  before promoting a task branch that may contain branch-local session entries or diagram sidecars.
  Treat `ok: false` or any `issues` as a merge blocker until the orchestrator or user resolves them.
- MCP remains read-only for this workflow. Do not expect it to apply a fuse, delete source files, or
  complete a merge. Use the returned `merge_checkpoint_command` and `apply_command` as operator
  guidance, then either run `memory-seed session merge-branch --branch <branch>` for the one-step
  merge+fuse+commit, or apply through `session fuse --apply` only during an in-progress inspected
  merge.
- A previewed diagram sidecar is valid only when its parent entry already exists on the base/main tree
  or the parent branch entry is accepted for promotion in the same preview. Orphan or malformed
  sidecars must block promotion.

If MCP tools are unavailable, run `memory-seed branch status` and
`memory-seed session merge-branch --branch <branch> --dry-run` directly from the integration tree
and report the same fields: warnings/issues, planned entries, planned sidecars, source removals,
and the command that would perform the merge.

## Dependency Strategy

Worktrees isolate source edits. Local environments isolate runtime state. Shared caches reduce disk
cost. Dependency definition files are orchestrator-owned shared files.

### Dependency Tiers

Every task packet declares a `dependency_tier`:

- `none` — read-only work; no environment setup required.
- `isolated` — normal writing work; each worktree gets its own local environment (e.g. `.venv`,
  `node_modules`), never one live environment shared with another parallel writer.
- `dependency-changing` — the worker may change dependency definitions or lockfiles. Treat this as a
  coordination event: the orchestrator decides whether to merge it first, merge it last, or pause and
  rebase other worker branches before trusting their validation.

### Shared Dependency Files

Dependency definition files and lockfiles are orchestrator-owned shared files, same tier as the
control-plane files below: `pyproject.toml`, `requirements*.txt`, `uv.lock`, `package.json`,
`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`. Workers on `none` or `isolated` tiers must not
edit these files; only a `dependency-changing` worker may, and only within its assigned scope.

### Shared Caches

A read-only shared package/download cache (e.g. pip/uv/npm cache directories) may be shared across
worktrees to reduce disk cost. Never share one live installed environment or virtualenv across
parallel writing worktrees — that reintroduces the mutable-shared-state risk worktrees exist to
prevent.

### Tmux As Optional Control Room

Tmux (or any terminal multiplexer) is an optional operator convenience for watching multiple
worktrees at once. It is not part of the portable contract: Git branch, worktree, task packets,
validation records, and handoff evidence remain the contract regardless of which terminal tooling the
orchestrator uses.

## Conflict Escalation

Workers may resolve conflicts in files they clearly own for the task.

Shared/control-plane conflicts are the Shared / control-plane STOP category in
`risk_signaling.md`: do not let a worker resolve them unless the packet explicitly assigns that
write and names the conflict owner.

Escalate to the orchestrator or human for:

- shared control-plane files such as `AGENTS.md`, `.memory-seed/agent-rules.md`, `.memory-seed/policy.md`, or skill registry files
- dependency definition files and lockfiles (see Dependency Strategy) unless the worker's packet declares `dependency_tier: dependency-changing`
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
- If a worker branch does write session memory, each new entry must carry `branch: <task-branch>`
  (`memory-seed session append` captures it automatically from git).
  Existing entries are immutable. Branch diagram sidecars may be fused only when the parent entry is
  already on the base/main tree or is accepted for promotion in the same fuse.
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
