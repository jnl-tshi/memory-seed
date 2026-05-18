---
memory-system-version: 1.4
tags:
  - ai-memory
  - agent-rules
  - operating-mode
---

# Agent Rules

These rules define how AI agents should use this project's local memory system.

## Core Principle

The `.AGENTS` folder is the source of operational memory for this repository. Keep it small, navigable, and local-first so an agent can quickly understand the project without loading historical noise by default.

Memory Seed targets file-reading AI coding agents. Keep shared memory in plain Markdown, use predictable paths, keep read order explicit, and avoid vendor-specific assumptions in the memory core. Tool-specific routing files may exist, but they must point into the same `.AGENTS/` system.

## Reusable Seed Files

The reusable seed control plane is:

```text
AGENTS.md        # Generic agent entry point
CLAUDE.md        # Claude Code routing file
GEMINI.md        # Gemini CLI routing file
.AGENTS/
  agent-rules.md
  project-bootstrap.md
```

Project-specific operating files are generated during bootstrap and are not version-archived with the seed:

```text
.AGENTS/
  index.md
  context.md
  style.md
  sessions/
```

## Active Memory Structure

Required files and folders:

```text
.AGENTS/
  agent-rules.md        # This workflow contract
  index.md              # Top-level pointer and read order
  context.md            # Authoritative project context, current state, durable facts
  style.md              # Writing, naming, and formatting conventions
  sessions/             # Append-only dated session logs
```

`project-bootstrap.md` may exist but is not part of the operating-mode read order.

## Mode Check Routine

Before operating-mode startup, check whether all initialized memory files exist:

```text
.AGENTS/index.md
.AGENTS/context.md
.AGENTS/style.md
.AGENTS/sessions/
```

If all exist, proceed with the start-of-work routine. If any are missing, use `.AGENTS/project-bootstrap.md` to initialize or repair the memory system before reading missing operating files.

## Start-of-Work Routine

At the start of a session after the mode check confirms operating mode:

1. Read `.AGENTS/agent-rules.md`.
2. Read `.AGENTS/index.md`.
3. Read `.AGENTS/context.md`, especially `Fast Orientation` and `Current State`.
4. Read `.AGENTS/style.md` when writing or editing project documentation.
5. Read recent `.AGENTS/sessions/*` only when historical detail is needed.

If the repository root is unclear, identify it first and note any uncertainty in `context.md` only if it is durable project context.

## Orchestration Levels

Use the lowest orchestration level that can complete the work safely. Higher levels trade more tokens and coordination cost for better coverage, validation, and risk control.

### Level 0: Direct Work

Use for simple, low-risk changes with clear scope.

- One agent works directly.
- Keep context loading minimal.
- Verify with the smallest relevant check.

### Level 1: Plan, Implement, Verify

Use for normal project work.

- Inspect the relevant files first.
- State the approach briefly when useful.
- Implement the change.
- Run targeted verification before reporting completion.

### Level 2: Orchestrator, Worker, Validator

Use for large, multi-file, ambiguous, or risky changes where splitting work reduces risk or improves throughput.

- Orchestrator owns scope, sequencing, context budget, and integration.
- Workers own bounded, non-overlapping subtasks.
- Validator checks behavior, tests, regressions, and policy fit.
- If the active agent cannot spawn subagents, follow the same phases serially.

### Level 3: Research And Human Checkpoints

Use for architecture changes, security-sensitive work, publishing/release changes, destructive operations, or decisions where current best practice may matter.

- Research first when the answer may have changed or external standards matter.
- Summarize evidence and tradeoffs before implementation.
- Ask for human approval at meaningful checkpoints.
- Keep validation records explicit enough for future agents to audit the decision.

### Token And Model Budget Policy

- Default to the least expensive level that can safely handle the task.
- Use worker/validator splits only when they reduce risk, reduce wall-clock time, or improve review quality enough to justify the extra context.
- Treat model choice as capability tiers: economy for simple extraction or formatting, standard for routine implementation, and frontier for architecture, security, ambiguous debugging, or high-impact validation.
- Prefer narrow context packets for workers and validators instead of handing them the whole repository history.

## File Change Permission Model

Agents must treat `.AGENTS` and agent-routing files according to these buckets.

### Locked Unless Explicitly Requested

These files define the reusable control plane for agents. Do not modify them unless the user explicitly asks for agent workflow, bootstrap, routing, or memory-structure changes.

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.AGENTS/agent-rules.md`
- `.AGENTS/project-bootstrap.md`

Also locked unless explicitly requested:

- Adding new top-level `.AGENTS` files.
- Deleting existing `.AGENTS` files.
- Renaming `.AGENTS` files or folders.
- Reorganizing the `.AGENTS` structure.
- Recreating obsolete files such as `current.md`, `project-memory.md`, or `memory.md`.
- Editing prior session logs except for explicit repair, archival cleanup, or user-requested correction.

### End-Of-Session Restricted Updates

These files should normally be updated only during the end-of-session routine, after the agent has enough context to distinguish durable facts from temporary work.

- `.AGENTS/context.md`: Update when durable/current project facts changed, including project structure, current priorities, artifact paths, stable decisions, operational risks, or project type/risk classification.
- `.AGENTS/index.md`: Update only when read order, hot facts, active workflow, or key project pointers changed.
- `.AGENTS/style.md`: Update only when durable conventions, project type/risk implications, security posture, coding standards, documentation standards, or workflow conventions changed.

Do not edit these files for ordinary implementation details, temporary observations, or raw session history. Put that detail in `.AGENTS/sessions/YYYY-MM-DD.md`.

Immediate-update exception: update `.AGENTS/context.md`, `.AGENTS/index.md`, or `.AGENTS/style.md` during a session only when leaving the current content stale would immediately mislead the active work, route an agent to the wrong files, preserve an unsafe assumption, or cause repeated incorrect actions.

For restricted files, the agent must be able to explain why the file's ownership scope was affected.

### Routine Append

- `.AGENTS/sessions/YYYY-MM-DD.md`: Append concise notes for meaningful work completed on that date. Do not log trivial edits, routine command output, or temporary observations unless they affect future handoff, risk, or decisions.

Session logs are append-only. Today's file may be appended during normal work or at the end of the session. Prior dated session files must not be edited unless the user explicitly asks for repair, archival cleanup, or correction.

## End-of-Work Routine

At the end of meaningful work:

1. Append a concise note to `.AGENTS/sessions/YYYY-MM-DD.md`.
2. Review whether `.AGENTS/context.md` needs consolidation because project structure, current priorities, workflow logic, artifacts, durable decisions, or operational risks changed.
3. Update `.AGENTS/index.md` only when read order, hot facts, active workflow, or key project pointers changed.
4. Update `.AGENTS/style.md` only when durable conventions, project type/risk implications, security posture, coding standards, documentation standards, or workflow conventions changed.

Session logs are append-only. Do not rewrite or compress old session entries unless the user explicitly asks for archival cleanup.

## Context Ownership

`context.md` owns:

- Project purpose and business goal.
- Fast orientation for new agents.
- Current state, active priorities, and immediate risks.
- Repository traversal guidance and important folders/files.
- Stable model, routing, production, and artifact decisions.
- Memory workflow rules that affect future agents.

`index.md` owns:

- Minimal read order.
- Short pointers to the files that matter.
- Current hot facts that prevent loading the wrong notebook or stale artifact path.

`sessions/*` owns:

- Chronological work logs.
- Experiments, failed attempts, temporary observations, and detailed implementation notes.
- Evidence that may later be promoted into `context.md`.

## Consolidation Routine

Periodically review recent session logs and promote only stable, reusable facts into `context.md`. Keep `context.md` concise enough for fast agent orientation, but complete enough to traverse the repository and understand why the project is structured as it is.

Examples of facts worth promoting:

- Notebook ownership changes.
- Stable artifact paths.
- Workflow objective changes.
- Production runtime assumptions.
- Current evaluation criteria.
- Known stale outputs or rerun requirements.

Examples that should usually stay in sessions only:

- One-off debugging traces.
- Temporary hypotheses.
- Intermediate command outputs.
- Superseded experiments.

## Memory Doctor Checklist

A clean `.AGENTS` folder should satisfy all of the following:

- `AGENTS.md` exists and routes initialized projects to operating mode.
- `.AGENTS/project-bootstrap.md` exists, is marked bootstrap-only, and is not required in the operating-mode read order.
- `.AGENTS/index.md` points to the active files only.
- `.AGENTS/context.md` contains `Fast Orientation`, `Current State`, and `Project Type And Risk`.
- `.AGENTS/sessions/` contains dated append-only logs.
- `.AGENTS/agent-rules.md` describes operating-mode files without requiring bootstrap guidance.
- The file change permission buckets are present and distinguish locked, restricted, and routine append files.
- End-of-session restricted files are consolidated deliberately, not edited for temporary observations.
- Important workflow/output/artifact changes are represented in `context.md`, not only in a session log.

## Session Log Format

Use dated files under `.AGENTS/sessions/` with short entries such as:

```markdown
## 2026-05-02 - Project setup and workflow update

- Updated the project workflow or implementation area touched today.
- Recorded the key decision, artifact, or file path that future agents need.
- Follow-up: note any rerun, validation, review, or unresolved risk.
```

Prefer concise bullets. Capture meaningful decisions, durable changes, follow-up risk, or handoff context. Do not log trivial work or every command.

## Public Memory Hygiene

Treat `.AGENTS` files as potentially publishable unless the user explicitly says the repository will always remain private. Do not write secrets, credentials, tokens, private keys, sensitive account details, client confidential information, or unnecessary personal data into `context.md`, `style.md`, `index.md`, or session logs.

When a project may become public, keep session entries focused on durable technical decisions and omit private local paths, private identities, and sensitive operational details unless the user explicitly asks to preserve them.

## Bootstrap Boundary

This repository is in operating mode only when `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and `.AGENTS/sessions/` exist.

Do not read or apply `.AGENTS/project-bootstrap.md` after operating mode is confirmed. Use it for brand-new projects, seed-only projects, or incomplete `.AGENTS` folders.

If a user explicitly asks to bootstrap a new project, use `.AGENTS/project-bootstrap.md` as the bootstrap procedure for that new project. Do not apply bootstrap rules to this initialized project unless the user explicitly asks to rebuild the memory system.







