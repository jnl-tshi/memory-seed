---
title: Memory Seed Worktree, tmux, and Dependency Strategy Source
status: refined-into-active-plan
created: 2026-07-04
repo: jnl-tshi/memory-seed
scope:
  - git-worktrees
  - tmux
  - multi-agent-development
  - dependency-strategy
  - control-plane-integration
---

# Memory Seed Worktree, tmux, and Dependency Strategy Source

> **Status: RESOLVED SOURCE, refined 2026-07-04.** The active implementation proposal is
> [`../worktree-dependency-strategy-plan.md`](../worktree-dependency-strategy-plan.md). This file is
> retained as source context only.

## Executive summary

Memory Seed should treat **Git worktrees** and **tmux** as the practical execution layer for multi-agent development, while keeping Memory Seed itself as the **local-first control plane**: rules, task packets, memory, validation, handoff, and durable session logging.

The recommended model is:

```text
Memory Seed control plane = rules, memory, task packets, handoff, validation
Git branches              = reviewable lines of work
Git worktrees             = isolated folders for parallel code-writing agents
tmux                      = optional terminal/session control room
Dependency strategy       = policy for local environments, shared caches, and shared dependency files
```

The strongest beginner rule is:

```text
One task = one branch = one worktree = one bounded task packet
```

For dependencies:

```text
Worktrees isolate source edits.
Local environments isolate runtime state.
Shared caches reduce disk cost.
Dependency definition files are orchestrator-owned shared files.
```

Memory Seed should not become a hosted agent orchestrator or automatically spawn agents. Instead, it should document and eventually scaffold the workflow using preview-first Markdown/YAML artifacts: task packets, branch names, worktree paths, validation checklists, review checklists, and final handoff templates.

---

## 1. Context

This document consolidates a learning conversation about:

- beginner Git worktree concepts;
- how worktrees appear in Git history;
- how tmux and worktrees support multi-agent AI development;
- how Memory Seed’s control plane should integrate that workflow;
- how dependency folders such as `.venv/`, `node_modules/`, build caches, package caches, and lockfiles should be managed across multiple agents;
- synergies and clashes with Memory Seed’s current architecture.

The conversation used the `jnl-tshi/memory-seed` repository as the grounding project, especially:

- `docs/functionality-audit.md`;
- `memory_seed/seed/.memory-seed/agent-rules.md`;
- `memory_seed/seed/.memory-seed/skills/agent_collaboration.md`;
- `memory_seed/seed/.memory-seed/skills/local_compilation.md`;
- `memory_seed/seed/.memory-seed/skills/index.md`;
- `pyproject.toml`;
- `.gitignore`.

---

## 2. Beginner mental model

### 2.1 What a worktree is

A Git worktree is an additional working directory attached to the same repository history.

A beginner-friendly mental model:

```text
Branch   = a named line of Git history
Worktree = a physical folder where that branch is checked out
Commit   = a saved point in history
```

Example:

```bash
git worktree add ../agent-login -b agent-login
```

This creates:

```text
folder: ../agent-login
branch: agent-login
```

If commits are made in `../agent-login`, the branch and commits appear in the Git graph. The worktree folder itself does not appear in the graph.

```text
main
  |
  A---B---C
       \
        D---E  agent-login
```

### 2.2 What happens when a worktree is removed

Removing a worktree removes the physical folder, not necessarily the branch.

```bash
git worktree remove ../agent-login
```

The branch may still exist:

```bash
git branch
```

A branch can then be deleted after merge or abandonment:

```bash
git branch -d agent-login
```

Use `-d` for safe deletion. Git will complain if the branch has not been merged.

### 2.3 Why one worktree per task is safer

For multi-agent AI work, a worktree should usually be treated as a **task workspace**, not as a permanent identity folder for an agent.

Recommended:

```text
one task = one branch = one worktree
```

Avoid this as the default:

```text
agent-1-worktree/  # reused forever for unrelated tasks
```

Long-lived agent worktrees can accumulate:

- stale branches;
- uncommitted files;
- dependency drift;
- leftover build outputs;
- old assumptions from previous tasks.

Task-scoped worktrees are easier to review, clean up, and reason about.

---

## 3. Role of tmux

`tmux` should be treated as an optional **control room**, not a Memory Seed dependency.

A practical layout:

```text
tmux session: memory-seed-fanout

window 0: orchestrator / main repo
window 1: worker-a worktree
window 2: worker-b worktree
window 3: validator / read-only review
window 4: integration branch
```

This allows a human or orchestrator agent to supervise several workspaces at once.

Memory Seed should not require tmux because the project’s architecture is portable and vendor-neutral. Some users will work on Windows, some through IDE agents, some through hosted terminals, and some through plain shells.

Recommended framing:

```text
tmux is an operator convenience.
Git branches and worktrees are the portable contract.
Memory Seed owns the workflow and memory contract.
```

---

## 4. Existing Memory Seed alignment

Memory Seed already contains several pieces that align well with a worktree-based multi-agent workflow.

### 4.1 Control-plane architecture

Memory Seed is already designed as a local-first, Markdown-first control-plane system for AI coding agents. Durable state lives in `.memory-seed/` as plain files rather than a server or database.

Relevant control-plane surfaces include:

- `AGENTS.md` and thin per-agent routing files;
- `.memory-seed/agent-rules.md`;
- `.memory-seed/index.md`;
- `.memory-seed/policy.md`;
- `.memory-seed/skills/`;
- `.memory-seed/sessions/`;
- lifecycle hooks;
- MCP retrieval;
- optional Memory Lense UI.

### 4.2 Existing orchestration levels

`agent-rules.md` already defines orchestration levels:

```text
Level 0: Direct Work
Level 1: Plan, Implement, Verify
Level 2: Orchestrator, Worker, Validator
Level 3: Research And Human Checkpoints
```

The worktree/tmux workflow belongs mostly in **Level 2** and **Level 3**.

The important design choice is to keep `agent-rules.md` high-level. It should not become a long worktree tutorial. Instead, it should point agents to the lazy-loaded collaboration skill.

### 4.3 Existing `agent_collaboration.md` skill

The existing `agent_collaboration.md` skill is the correct home for the detailed workflow. It already covers:

- Git-first collaboration;
- branch and worktree coordination;
- task packets;
- worker handoffs;
- validation;
- merge conflict handling;
- orchestrator-owned session logging;
- shared-file policy;
- bounded review-to-rework loop.

This means the project does not need a new “multi-agent system” from scratch. It needs to strengthen and teach the existing collaboration contract.

---

## 5. Recommended multi-agent workflow

### 5.1 Overall flow

```text
agent-rules.md
  ↓
skills/index.md detects branch/worktree/subagent work
  ↓
agent_collaboration.md loads
  ↓
orchestrator creates task packets
  ↓
each writing worker gets one branch + one worktree
  ↓
workers commit and hand off evidence
  ↓
orchestrator merges, validates, reviews, logs
```

### 5.2 Gate model

The recommended workflow should follow the existing fan-out pattern:

1. **Scope Gate**  
   Decide whether parallel work is justified. Default to direct work unless the task is separable and the coordination cost is worth it.

2. **Exploration Gate**  
   Read-only agents inspect narrow questions and return evidence. They may share the current tree, but they must still verify `pwd` and `HEAD`.

3. **Plan Gate**  
   One orchestrator reconciles the findings, defines the architecture, assigns file ownership, and names the conflict owner.

4. **Worker Identity Gate**  
   Each worker proves it is in the right worktree at the right base commit before editing.

5. **Worktree Gate**  
   Each parallel code-writing worker gets a separate worktree and a bounded task packet.

6. **Pre-Review Validation Gate**  
   Each worker commits its own work and reports checks, failures, skipped checks, and risks.

7. **Integration Gate**  
   The orchestrator merges branches one at a time into an integration branch, inspecting and validating after each merge.

8. **Bounded Review-to-Rework Loop**  
   A validator reviews the integrated diff. Rework is capped, commonly at two iterations, before escalation.

9. **Final Handoff Gate**  
   The orchestrator writes the final handoff and durable session entry.

---

## 6. Worktree lifecycle commands

### 6.1 Check current repo status

```bash
pwd
git status
git branch --show-current
git status --short
```

A clean `git status --short` output is safest before creating a worktree.

### 6.2 List worktrees

```bash
git worktree list
```

### 6.3 Create a task worktree

```bash
git worktree add ../memory-seed-agent-login -b agent-login
```

More structured example:

```bash
git worktree add ../memory-seed-worktrees/fix-login -b jean/fix/login
```

### 6.4 Enter the worktree

```bash
cd ../memory-seed-worktrees/fix-login
git status
git branch --show-current
```

### 6.5 Commit worker changes

```bash
git status --short
git add <files>
git commit -m "Fix login validation"
```

### 6.6 Remove the worktree when done

```bash
git worktree remove ../memory-seed-worktrees/fix-login
```

### 6.7 Delete the branch after merge or abandonment

```bash
git branch -d jean/fix/login
```

Use force deletion only when intentionally abandoning unmerged work:

```bash
git branch -D jean/fix/login
```

---

## 7. Recommended path and branch conventions

### 7.1 Worktree paths

Suggested pattern:

```text
../memory-seed-worktrees/<topic>/<worker-slug>
```

Examples:

```text
../memory-seed-worktrees/fanout-docs/worker-a
../memory-seed-worktrees/fanout-docs/worker-b
../memory-seed-worktrees/link-validation/worker-c
```

### 7.2 Branch names

Use the repository convention first. If none exists, use:

```text
<owner>/<kind>/<topic>
```

Where `kind` is usually one of:

```text
feature
fix
refactor
test
docs
```

Examples:

```text
jean/docs/worktree-control-plane
agent-a/test/session-target-gating
agent-b/refactor/link-validation
```

---

## 8. Task packet template

Every writing worker should receive a narrow task packet.

```yaml
owner: "<human-or-agent-slug>"
role: "worker"
base_branch: "main"
base_sha: "<commit hash the worker must verify before editing>"
working_branch: "<owner>/<kind>/<topic>"
worktree: "../memory-seed-worktrees/<topic>/<worker>"
expected_pwd: "<absolute or project-relative worktree path>"
objective: "<one concrete outcome>"
integration_artifact: "pr|merge-request|patch|branch|handoff"
capability_tier: "economy|standard|frontier"
shared_file_policy: "orchestrator_only"
conflict_owner: "orchestrator"
allowed_files:
  - "<paths or globs the worker may edit>"
forbidden_files:
  - "AGENTS.md"
  - ".memory-seed/agent-rules.md"
  - ".memory-seed/policy.md"
  - ".memory-seed/index.md"
  - ".memory-seed/skills/index.md"
  - ".memory-seed/sessions/**"
  - "memory_seed/seed/**"
  - "pyproject.toml"
  - "requirements*.txt"
  - "uv.lock"
  - "package.json"
  - "package-lock.json"
  - "pnpm-lock.yaml"
  - "yarn.lock"
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
  - "shared control-plane files changed"
  - "dependency definition files changed"
  - "lockfile conflict"
  - "behavior conflict rather than formatting conflict"
review_loop:
  current_iteration: 0
  max_iterations: 2
  escalation: "human-or-orchestrator"
```

---

## 9. Dependency strategy

### 9.1 The core problem

Worktrees isolate source files, but dependency folders can still cause problems.

With five worktrees, a naive setup may create:

```text
memory-seed-agent-a/.venv/
memory-seed-agent-b/.venv/
memory-seed-agent-c/.venv/
memory-seed-agent-d/.venv/
memory-seed-agent-e/.venv/
```

This is safe but can waste disk space.

The opposite approach — sharing one live virtual environment across all worktrees — saves space but creates hidden coupling.

Example failure mode:

```text
agent A upgrades a dependency
agent B's tests suddenly change
agent C can no longer reproduce its previous result
```

### 9.2 Recommended rule

```text
Each writing worktree may have its own live environment.
Package-manager caches may be shared outside the repo.
Dependency definition files are orchestrator-owned shared files.
```

### 9.3 What should be isolated per worktree

Usually isolate:

```text
.venv/
node_modules/
.pytest_cache/
build outputs
coverage outputs
local test artifacts
editable installs
```

These are local workspace state. They should not be committed.

### 9.4 What can be shared outside the repo

Usually safe to share:

```text
pip/uv wheel caches
npm/pnpm/yarn package caches
model download caches
compiler caches when configured safely
Memory Lense cache outside the repo
```

The pattern should be:

```text
Shared cache outside repo:
  downloaded wheels/packages/models

Per-worktree environment:
  .venv/
  node_modules/
  installed editable package
  local test state
```

This mirrors the Memory Lense cache decision: caches can be rebuildable and external, while project files remain the source of truth.

### 9.5 Dependency definition files are shared files

Treat these as high-risk shared files:

```text
pyproject.toml
requirements*.txt
uv.lock
poetry.lock
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
```

Workers should not edit these unless the task packet explicitly allows it.

For Memory Seed specifically, `pyproject.toml` controls:

- package name;
- version;
- Python requirement;
- required dependencies;
- optional extras;
- console scripts;
- package data.

A dependency change therefore affects packaging, installation, validation, and release behavior.

### 9.6 Dependency tiers

Define three dependency tiers for multi-agent work.

#### Tier 0: no install

Use for read-only agents:

```text
research
review
planning
file inspection
architecture analysis
```

Policy:

```text
No .venv required.
No dependency install.
Can share current tree if read-only.
Must still verify pwd and HEAD before reporting.
```

#### Tier 1: isolated worktree environment

Use for normal code-writing workers.

Policy:

```text
Separate worktree.
Separate .venv or local dependency folder.
No dependency-definition edits.
Run targeted validation.
```

#### Tier 2: dependency-changing work

Use only when the task explicitly changes dependencies.

Policy:

```text
Separate branch.
Separate worktree.
May edit dependency definitions only if allowed.
Orchestrator integrates deliberately.
Fuller validation required.
```

### 9.7 Python setup for a normal worker

macOS/Linux:

```bash
cd ../memory-seed-worktrees/<topic>/<worker>
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m unittest
```

Windows PowerShell:

```powershell
cd ..\memory-seed-worktrees\<topic>\<worker>
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m unittest
```

For Memory Lense work:

```bash
pip install -e ".[lense]"
```

Use the optional extra only when the work actually needs Lense functionality.

### 9.8 Dependency preflight

Extend worker preflight when code execution is required:

```yaml
preflight:
  - "pwd"
  - "git rev-parse --show-toplevel"
  - "git rev-parse HEAD"
  - "git status --short"
  - "python --version"
  - "python -m pip --version"
  - "python -m pip show memory-seed || true"
```

For JavaScript/TypeScript projects, use equivalent commands:

```yaml
preflight:
  - "node --version"
  - "npm --version"
  - "npm ls --depth=0 || true"
```

---

## 10. Shared-file policy

### 10.1 Why this matters

Worktrees prevent uncommitted source-file collisions, but they do not automatically solve conflicts in shared files.

High-risk shared files include:

```text
session logs
lockfiles
seed templates
control-plane files
routing files
release files
generated binary artifacts
```

### 10.2 Default rule

```text
shared_file_policy: orchestrator_only
```

Workers should usually avoid:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.github/copilot-instructions.md
.memory-seed/agent-rules.md
.memory-seed/project-bootstrap.md
.memory-seed/index.md
.memory-seed/policy.md
.memory-seed/skills/index.md
.memory-seed/sessions/**
memory_seed/seed/**
pyproject.toml
lockfiles
```

### 10.3 Worker default behavior

Workers should return handoff evidence instead of writing durable memory.

Worker handoff should include:

```text
summary
files changed
commit hashes
validation run
validation result
known risks
conflicts or suspected conflicts
```

### 10.4 Orchestrator default behavior

The orchestrator owns:

```text
task decomposition
branch/worktree naming
base SHA verification
shared-file ownership
integration order
final validation
durable session logging
```

This prevents multiple temporary AI workers from fragmenting Memory Seed’s durable memory.

---

## 11. Integration strategy

### 11.1 Avoid octopus merges for code

Do not merge all worker branches at once.

Avoid:

```text
merge worker-a + worker-b + worker-c simultaneously
```

Prefer:

```text
merge worker-a
inspect diff
run targeted validation

merge worker-b
inspect diff
run targeted validation

merge worker-c
inspect diff
run targeted validation
```

### 11.2 Dependency-changing branches need deliberate sequencing

Dependency-changing branches can affect all other workers.

Options:

1. **Integrate dependency branch first**  
   Use when all workers need the new dependency.

2. **Integrate dependency branch last**  
   Use when the dependency change is isolated and should not disrupt other work.

3. **Stop and rebase workers**  
   Use when the dependency change is central and worker validation against the old base is no longer trustworthy.

The orchestrator should record which path was chosen and why.

---

## 12. Recommended additions to Memory Seed docs/control plane

### 12.1 Add a dependency strategy section to `agent_collaboration.md`

Suggested text:

```text
## Dependency Strategy

Writing workers may create worktree-local environments such as `.venv/` or `node_modules/`.
Do not share one live virtual environment across parallel writing worktrees.
Share package-manager caches outside the repository when the tool supports it.
Dependency definition files and lockfiles are shared files.
Workers must not edit dependency definitions unless the task packet explicitly allows it.
If dependencies change, the orchestrator integrates that branch deliberately and reruns validation for affected workers.
```

### 12.2 Add dependency fields to the task packet

Suggested additions:

```yaml
dependency_tier: "none|isolated|dependency-changing"
dependency_setup:
  - "python -m venv .venv"
  - "source .venv/bin/activate"
  - "pip install -e ."
dependency_shared_cache_policy: "allowed-outside-repo"
dependency_definition_policy: "orchestrator_only"
```

### 12.3 Add a tmux note to the collaboration skill

Suggested text:

```text
tmux may be used as an operator control room, with one window per orchestrator, worker, validator, or integration branch. tmux is optional; Git branch/worktree state and task packets are the portable contract.
```

### 12.4 Avoid adding this detail to always-read `agent-rules.md`

`agent-rules.md` should remain concise and startup-safe. It should continue to point to `agent_collaboration.md` for branch/worktree/multi-agent workflows.

---

## 13. Possible future CLI scaffold

A future command could emit workflow files but should not execute the workflow.

Possible command:

```bash
memory-seed workflow fanout --topic <slug> --workers 2 --dry-run
```

Possible generated outputs:

```text
task-packet Markdown files
suggested branch names
suggested worktree paths
dependency tier recommendations
validation checklist
review checklist
final handoff template
cleanup checklist
```

Initial constraints:

```text
preview-first
no agent spawning
no branch mutation
no worktree creation
no session-log writes
no PR creation
```

This preserves Memory Seed’s boundary as a local-first control plane rather than a runtime orchestrator.

---

## 14. Beginner-friendly runbook

### 14.1 Starting point

From the main repo:

```bash
git status --short
git branch --show-current
git worktree list
```

Only continue if the repo state is understood.

### 14.2 Create worker worktree

```bash
git worktree add ../memory-seed-worktrees/example-worker -b jean/docs/example-worker
```

### 14.3 Enter and verify

```bash
cd ../memory-seed-worktrees/example-worker
pwd
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
```

### 14.4 Set up local Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 14.5 Do the work

Stay inside the allowed file set.

Check status often:

```bash
git status --short
```

### 14.6 Validate

```bash
python -m unittest
```

Or run the smallest relevant command for the change.

### 14.7 Commit

```bash
git add <changed-files>
git commit -m "<short description>"
```

### 14.8 Handoff

Worker reports:

```text
Branch:
Worktree:
Commit:
Files changed:
Validation:
Risks:
Conflicts:
```

### 14.9 Integrate

Orchestrator merges one worker branch at a time.

### 14.10 Cleanup

After merge or abandonment:

```bash
git worktree remove ../memory-seed-worktrees/example-worker
git branch -d jean/docs/example-worker
```

---

## 15. Synergies

### 15.1 Git-native isolation fits Memory Seed’s architecture

Memory Seed is local-first and file-based. Git worktrees are also local and Git-native. They improve parallelism without introducing a database, service, or hosted scheduler.

### 15.2 Existing collaboration skill already has the right shape

The project already has `agent_collaboration.md`, task packets, worktree guidance, shared-file policy, integration gates, and review loops. The dependency strategy can extend this rather than creating a new system.

### 15.3 Multi-user session memory complements multi-agent work

Per-user session targets help human contributors avoid same-file conflicts. AI workers can remain handoff-only by default, while the orchestrator writes the durable memory entry.

### 15.4 Memory Lense becomes more valuable

Fan-out work generates more decisions, branches, commits, handoffs, and session entries. Memory Lense’s search, timeline, graph, and reader/detail views become more useful when multi-agent development produces a richer project history.

### 15.5 Task packets align with beginner learning

Task packets make implicit expectations explicit:

```text
where to work
what branch to use
which files are allowed
which files are forbidden
what validation to run
what handoff evidence to return
```

This is especially useful for beginners and for AI agents that otherwise infer too much.

---

## 16. Clashes

### 16.1 Worktrees do not solve all shared-state problems

Worktrees isolate folders, but not all project state is safely independent. Shared files can still conflict.

Examples:

```text
session logs
lockfiles
seed templates
control-plane files
release metadata
```

### 16.2 Dependencies create hidden coupling

If workers share one live environment, one agent can change another agent’s runtime behavior without touching Git-tracked files.

### 16.3 Dependency duplication can be expensive

Separate `.venv/` or `node_modules/` folders are safer, but they cost disk space.

### 16.4 Parallelism increases integration burden

More workers means more branches, validation outputs, review findings, and cleanup. For small tasks, this is worse than direct work.

### 16.5 Product boundary risk

If Memory Seed starts spawning agents, controlling tmux, creating branches, or opening worktrees automatically, it risks becoming a runtime orchestrator rather than a local-first control plane.

---

## 17. Mitigations

### 17.1 Use the lowest sufficient orchestration level

Do not fan out by default.

Use parallel work only when:

```text
file ownership is separable
coordination cost is justified
validation boundaries are clear
shared files can be protected
```

### 17.2 Make preflight mandatory

Before worker edits, require:

```bash
pwd
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
```

For executable work, add dependency/runtime checks.

### 17.3 Make shared files orchestrator-owned

Default:

```yaml
shared_file_policy: "orchestrator_only"
```

Workers only touch shared files when explicitly assigned.

### 17.4 Prefer per-worktree live environments

Use one `.venv/` or equivalent local dependency folder per writing worktree.

Avoid sharing one live environment across writing agents.

### 17.5 Share caches outside the repo

Reduce disk cost by sharing package/download caches outside the repository, not by sharing live installed environments.

### 17.6 Integrate one branch at a time

Sequential integration keeps causality clear and makes conflicts easier to reason about.

### 17.7 Keep scaffolding preview-first

A future CLI command should generate files and recommendations only until the workflow has proved itself repeatedly.

---

## 18. Recommended implementation sequence

### Phase 1: Documentation-only hardening

Update `agent_collaboration.md` with:

- dependency strategy;
- dependency tiers;
- tmux-as-control-room note;
- stronger task packet examples;
- cleanup checklist.

### Phase 2: Add examples

Add one or more example task packets:

```text
docs/examples/fanout-task-packet-python.md
docs/examples/fanout-task-packet-docs.md
docs/examples/fanout-task-packet-dependency-change.md
```

### Phase 3: Add validation guidance

Extend local compilation guidance with worktree-specific setup notes:

```text
verify current worktree
inspect project scripts
install only what the task needs
run smallest relevant check first
record skipped checks clearly
```

### Phase 4: Evaluate dry-run scaffold

Only after repeated use, consider:

```bash
memory-seed workflow fanout --topic <slug> --workers 2 --dry-run
```

The first version should emit suggested artifacts only.

### Phase 5: Consider optional automation later

Only if the dry-run scaffold proves valuable, evaluate whether any safe automation should be added. Even then, avoid agent spawning and branch mutation by default.

---

## 19. Proposed addition: dependency strategy block

This is a ready-to-paste block for `agent_collaboration.md`.

````markdown
## Dependency Strategy

Worktrees isolate source edits, but dependency folders and caches require a separate policy.

- Writing workers may create worktree-local environments such as `.venv/`, `node_modules/`, build caches, and test caches.
- Do not share one live virtual environment or installed dependency folder across parallel writing worktrees.
- Share package-manager download caches outside the repository when the tool supports it.
- Dependency definition files and lockfiles are shared files.
- Workers must not edit dependency definitions unless the task packet explicitly allows it.
- If dependencies change, the orchestrator integrates that branch deliberately and reruns validation for affected workers.

Use dependency tiers:

- `none`: read-only work; no install required.
- `isolated`: normal writing work; create a local environment inside the worktree.
- `dependency-changing`: dependency definitions or lockfiles may change; orchestrator-owned integration and broader validation required.

Recommended task-packet fields:

```yaml
dependency_tier: "none|isolated|dependency-changing"
dependency_setup:
  - "<commands needed to prepare this worktree>"
dependency_definition_policy: "orchestrator_only"
dependency_shared_cache_policy: "allowed-outside-repo"
```
````

---

## 20. Proposed addition: tmux note

This is a ready-to-paste block for `agent_collaboration.md`.

````markdown
## tmux Control Room

`tmux` may be used as an operator control room, with one window or pane per orchestrator, worker, validator, or integration branch.

Example layout:

```text
tmux session: <project-topic>
window 0: orchestrator / main repo
window 1: worker-a worktree
window 2: worker-b worktree
window 3: validator / read-only review
window 4: integration branch
```

`tmux` is optional. The portable contract is the Git branch, Git worktree, task packet, validation record, and handoff evidence.
````

---

## 21. Final recommendation

Memory Seed should integrate tmux, worktrees, and dependency strategy as a **documented collaboration workflow**, not as automatic orchestration.

The durable project rule should be:

```text
Memory Seed coordinates the workflow.
Git provides isolation and history.
tmux helps humans supervise terminals.
Local environments isolate runtime state.
Shared caches reduce disk cost.
The orchestrator owns integration and durable memory.
```

This gives Memory Seed a strong foundation for multi-agent AI development while preserving its core identity:

```text
local-first
Markdown-first
Git-native
vendor-neutral
human-auditable
safe for gradual adoption
```
