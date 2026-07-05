---
memory-system-version: 2.16
tags:
  - memory-seed
  - agent-rules
  - operating-mode
---

# Agent Rules

These rules define how AI agents use the nearest `.memory-seed/` runtime.

## Core Principle

The active runtime is the nearest `.memory-seed/` directory discovered by walking upward from the current working directory. Keep the runtime small, navigable, local-first, and readable by file-reading AI coding agents.

Memory Seed stores shared memory in plain Markdown with predictable paths, explicit read order, and minimal vendor-specific assumptions. Tool-specific routing files may exist, but they must point into `AGENTS.md` and the same `.memory-seed/` runtime instead of creating separate vendor memories.

## Runtime Structure

The v2 runtime is:

```text
.memory-seed/
  agent-rules.md         # operating-mode workflow contract
  project-bootstrap.md   # bootstrap and repair procedure
  index.md               # bootstrap-generated project orientation and active state
  policy.md              # bootstrap-generated behavioral constraints only
  skills/                # lazy-loaded execution runbooks
  sessions/              # append-only dated work logs
  archive/               # archived prior control-plane snapshots
```

## Runtime Discovery

Before operating:

1. Start from the current working directory.
2. Walk upward toward the filesystem root.
3. Use the nearest ancestor containing `.memory-seed/`.
4. If no `.memory-seed/` exists, fall back to `.AGENTS/` only for legacy projects.

A nested project folder with its own `.memory-seed/` is a sub-project runtime. Work under that folder uses the sub-project runtime.

## Sub-Project Runtime Creation

Create a nested `.memory-seed/` runtime only when a sub-project has distinct long-lived context, policy, workflows, risks, outputs, or memory needs. Do not create a sub-project runtime just because a folder exists.

Ask the user before creating a nested runtime unless they explicitly requested sub-project memory setup. Load `.memory-seed/skills/subproject_runtime.md` for the full creation, inheritance, bootstrap-target, and parent/root summary workflow.

## Mode Check Routine

Operating mode is available when the active runtime contains:

```text
.memory-seed/agent-rules.md
.memory-seed/project-bootstrap.md
.memory-seed/skills/
.memory-seed/sessions/
.memory-seed/archive/
```

If any reusable control files or directories are missing, use `.memory-seed/project-bootstrap.md` long enough to repair the runtime before continuing.

If the reusable control plane exists but `.memory-seed/index.md` or `.memory-seed/policy.md` is missing, the project is seeded but not bootstrapped. Use `.memory-seed/project-bootstrap.md` to inspect the project, ask targeted questions, and generate those project-specific memory files before operating mode.

## Operating Mode Start

At the start of work:

1. Read `AGENTS.md`.
2. Discover the nearest `.memory-seed/` runtime.
3. Read `.memory-seed/agent-rules.md`.
4. Read `.memory-seed/index.md`, especially `Active State`, `Topology`, `Inheritance`, and `Lazy Skills`.
5. Read inherited parent policy only when the active index says policy inheritance is enabled.
6. Read `.memory-seed/policy.md`.
7. Establish current project state: read the newest session document in full (and skim the one before it), selected by session date across `.memory-seed/sessions/YYYY-MM-DD.md` and `.memory-seed/sessions/YYYY-MM-DD/<user>.md`. Read it directly â€” do not use `memory_search` to find the latest state (see Recency vs. Topical Retrieval). A SessionStart hook injects this automatically where supported; do the read yourself when it is not.
8. Read `.memory-seed/skills/index.md` as the deterministic skill trigger registry.
9. Load full `.memory-seed/skills/*.md` runbooks only when the trigger registry matches the current task.
10. If `.agents/_registry.yaml` exists at the workspace root, read it and load all persona files with `status: active`. Apply persona rules alongside this agent-rules.md and policy.md. Record `agent_name` (the persona's slug) in every session log entry this turn.

When multiple personas are active, the one most relevant to the current task governs. Default to the first active entry in `_registry.yaml` when ambiguous.

Do not read or apply `.memory-seed/project-bootstrap.md` during normal operating mode unless the runtime is missing or incomplete.

## History Retrieval And Conflict Resolution

Use MCP history retrieval when prior decisions, reason, unresolved risks, architecture, policy, bootstrap behavior, release history, or "why was this done" matters. Load `.memory-seed/skills/history_retrieval.md` for retrieval mechanics, `memory_search` and `memory_get_chunk` payloads, result interpretation, direct-file fallback, and conflict handling.

### Recency vs. Topical Retrieval

Newest-state questions use direct session-file reads by date. Topical questions use `memory_search`, with consequential results fetched by `memory_get_chunk`. These are different workflows and should not be substituted for each other.

Current files are the active authority: `.memory-seed/index.md`, `.memory-seed/policy.md`, active `.memory-seed/skills/*.md`, and source/config files for implementation truth. Session history is evidence and reason, not automatic authority.

If the conflict remains ambiguous or unresolved, ask the user before changing durable design, policy, bootstrap behavior, memory structure, release behavior, or similarly consequential workflow.
## Inheritance

Default inheritance for sub-project runtimes:

- Policy: inherit parent policy unless locally disabled.
- Skills: inherit parent skills unless locally disabled or overridden.
- Active state: local only.
- Sessions: local only.

Record deviations in `.memory-seed/index.md`.

Inside a sub-project runtime, local `index.md`, local `policy.md`, and local skills govern work under that runtime boundary. Parent policy and parent skills apply only where the local runtime inherits them and has not explicitly overridden or disabled them. If parent and local rules conflict and inheritance intent is unclear, ask the user before applying the conflicting rule.

## Orchestration Levels

Use the lowest orchestration level that can complete the work safely. Higher levels trade more tokens and coordination cost for better coverage, validation, and risk control.

### Level 0: Direct Work

Use for simple, low-risk changes with clear scope.

- One agent works directly.
- Keep context loading minimal.
- Verify with the smallest relevant check.

### Level 1: Plan, Implement, Verify

Use for normal project work.

- Inspect relevant files first.
- State the approach briefly when useful.
- Implement the change.
- Run targeted verification before reporting completion.

### Level 2: Orchestrator, Worker, Validator

Use for large, multi-file, ambiguous, or risky changes where splitting work reduces risk or improves throughput.

- Orchestrator owns scope, sequencing, context budget, and integration.
- Workers own bounded, non-overlapping subtasks.
- Validator checks behavior, tests, regressions, and policy fit.
- Load `.memory-seed/skills/agent_collaboration.md` for subagents, branch/worktree coordination, or multi-developer agent workflows.
- If the active agent cannot spawn subagents, follow the same phases serially.

### Level 3: Research And Human Checkpoints

Use for architecture changes, security-sensitive work, publishing/release changes, destructive operations, or decisions where current best practice may matter.

- Research first when the answer may have changed or external standards matter.
- Summarize evidence and tradeoffs before implementation.
- Ask for human approval at meaningful checkpoints.
- Keep validation records explicit enough for future agents to audit the decision.

## Token And Model Budget Policy

- Default to the least expensive level that can safely handle the task.
- Use worker/validator splits only when they reduce risk, reduce wall-clock time, or improve review quality enough to justify the extra context.
- Treat model choice as capability tiers: economy for simple extraction or formatting, standard for routine implementation, and frontier for architecture, security, ambiguous debugging, or high-impact validation.
- Prefer narrow context packets for workers and validators instead of handing them the whole repository history.

## File Ownership

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`: routing files.
- `.memory-seed/agent-rules.md`: operating workflow and memory ownership rules.
- `.memory-seed/project-bootstrap.md`: bootstrap and repair procedure.
- `.memory-seed/index.md`: rich project orientation, current state, topology, inheritance, and skill pointers.
- `.memory-seed/policy.md`: behavioral constraints only.
- `.memory-seed/skills/*.md`: task-specific runbooks, loaded on demand.
- `.memory-seed/sessions/YYYY-MM-DD.md` or `.memory-seed/sessions/YYYY-MM-DD/<user>.md`: append-only chronological work history.
- `.memory-seed/archive/`: archived prior control-plane states.

## Change Permission Model

Locked unless the user asks for memory workflow, bootstrap, routing, versioning, or control-plane changes:

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.memory-seed/agent-rules.md`
- `.memory-seed/project-bootstrap.md`
- `.memory-seed/policy.md`

Also locked unless explicitly requested:

- Adding new top-level `.memory-seed` files.
- Deleting existing `.memory-seed` files.
- Renaming `.memory-seed` files or folders.
- Reorganizing the `.memory-seed` structure.
- Recreating obsolete legacy memory files from older layouts.
- Editing prior session logs except for explicit repair, archival cleanup, or user-requested correction.

Restricted updates:

- `.memory-seed/index.md`: update when topology, active state, inheritance, current risk, or skill pointers changed.
- `.memory-seed/policy.md`: update only when durable behavioral constraints changed.
- `.memory-seed/skills/*.md`: update only when the corresponding reusable runbook changes.

Immediate durable-memory update exception: update `.memory-seed/index.md`, `.memory-seed/policy.md`, or an active skill during a session only when leaving the current content stale would immediately mislead active work, route an agent to wrong files, preserve an unsafe assumption, or cause repeated incorrect actions.

For restricted files, the agent must be able to explain why the file's ownership scope was affected.

Routine append:

- Active session target (`memory-seed session target`): append concise notes after meaningful work, before the current turn ends.

Do not rewrite old session entries unless the user explicitly asks for repair, archival cleanup, or correction.

## Working Principles

Cross-cutting principles that apply to any agent and any task:

- **POC-gate before scaling a risky or hard-to-verify automated method.** Prove a new editing or transformation pipeline on one throwaway case the user can validate, before applying it broadly.
- **Verification split.** State plainly what the agent can verify (for example file integrity, structural checks, diffs) versus what only the user can verify (for example an app opens the artifact without error). Never imply you verified the latter.
- **Read share-aware copies of locked files.** When another application holds a file open, read the last-saved bytes via a shared read handle rather than failing or assuming the content is stale.
- **Decision ladder before adding code.** Before writing new code, ask: does it need to exist, is it already in the codebase, and does stdlib or the native platform already handle it. Note briefly why something was deferred instead of silently dropping it.
- **Do not strip terse guards without understanding why.** A short validation or ownership check (a date-format guard, an is_ours ownership check, an isinstance guard) can look like boilerplate; read what it protects against before removing or simplifying it.
- **Default to plain text; reserve Mermaid for spatial, temporal, or concurrent structure.** Use a plain sentence or list for a decision's rationale by default. Reach for a Mermaid diagram only when the content is genuinely spatial, temporal, or concurrent — sequence flows across components, entity/schema relationships, or topology — where a diagram is clearly higher-signal than prose. Keep Mermaid blocks small, and double-check bracket/arrow/quote syntax before committing. Also check semantic freshness: roadmap diagrams must be updated when shipped work changes status, not merely kept syntactically valid. A broken or stale block renders as misleading raw text with no fallback.
- **Link commits to the decision entry that motivated them.** When a commit implements a logged decision, append a `Memory-Entry: <entry_id>` trailer to the commit message. Optionally backfill the entry's `commits:` field with the full 40-character SHA — but only while that entry is still the newest one, in the same turn; after that, the trailer alone carries the link. This is a convention, not an enforced hook.
- **Use qualitative risk tiers before acting.** For ambiguous, destructive, irreversible, externally visible, financial, security-sensitive, or shared-control-plane actions, load `.memory-seed/skills/risk_signaling.md` and choose Proceed, Proceed-and-flag, Propose-and-wait, or Stop from observable risk rather than numeric confidence.

## End Of Turn

After any turn where meaningful work was completed, append a concise entry to the active session target before the turn ends. Deferring or batching session log writes is a discipline failure.

Load `.memory-seed/skills/end_of_turn.md` for the full ESR checklist: session entry, consolidation review, policy/index/skill review, verification, orphan and artifact sweep, persona evolution, skill evolution, unregistered persona check, and baseline-promotion review.

Load `.memory-seed/skills/session_logging.md` for session frontmatter, entry YAML, DRAFT labels, entry shapes, append-only chronology, `related_entries`, and examples.

### Consolidation Review Triggers

Review recent session logs for durable-memory promotion when meaningful session volume, project direction, release behavior, policy, architecture, migration, bootstrap repair, security posture, or reusable workflow state has changed. Use `.memory-seed/skills/memory_consolidation.md` for the detailed compact-and-promote workflow.

These triggers require review, not automatic edits. Promote stable conclusions, not full decision history.

## Skill Loading

Skills are lazy-loaded runbooks. Read `.memory-seed/skills/index.md` first as the one-stop deterministic trigger registry. Load full skill runbooks only when the registry matches the task.

- `index.md`: deterministic trigger registry; read during startup before loading full skills.
- `agent_collaboration.md`: coordinating subagents, branch/worktree work, and multi-developer agent workflows.
- `history_retrieval.md`: MCP retrieval mechanics, topical-vs-recency retrieval, and history/current-authority conflict handling.
- `session_logging.md`: session log schema, DRAFT labels, examples, `related_entries`, and append-only chronology.
- `end_of_turn.md`: full ESR checklist, consolidation review, artifact sweep, persona/skill evolution, and baseline-promotion review.
- `memory_hygiene.md`: publishable-memory posture, secrets minimization, and reusable-template hygiene.
- `risk_signaling.md`: qualitative risk tiers and STOP categories for ambiguous, destructive, irreversible, security-sensitive, externally visible, financial, or shared-control-plane actions.
- `subproject_runtime.md`: nested runtime creation, inheritance choices, bootstrap target boundaries, and parent/root summaries.
- `code_search.md`: searching source code or repo structure efficiently.
- `data_architecture.md`: changing durable data structures, indexes, schemas, or retrieval behavior.
- `local_compilation.md`: validating local build/test/package/run behavior.
- `memory_consolidation.md`: compacting session memory and promoting durable facts.
- `memory_doctor.md`: validating runtime health and migration integrity.
- `release_publishing.md`: preparing or publishing package releases.
- `security_triage.md`: reviewing security-sensitive changes.

Evaluate registry rules in listed order, load every matching required skill, and keep the loaded set as small as the task safely allows. For sub-projects, use the nearest runtime's registry first; inherited parent registries apply only when enabled and not locally overridden or disabled.

### Code Search Trigger

For code search, repository exploration, symbol lookup, or broad codebase orientation, load `.memory-seed/skills/code_search.md` before broad grep sweeps or full-file reads.

### Memory Doctor Trigger

Load `.memory-seed/skills/memory_doctor.md` when runtime health, migration integrity, missing files, archive state, seed/live sync, or bootstrap completion is uncertain.

### Compact And Consolidation Trigger

Load `.memory-seed/skills/memory_consolidation.md` when reviewing compact output, promoting durable memory, reconciling session history with `index.md` / `policy.md`, or deciding whether long session logs need summarizing. Compact output is review input, not an automatic write plan.

## Public Memory Hygiene

Treat `.memory-seed` files as potentially publishable unless the user explicitly says the repository will always remain private. Do not write secrets, credentials, tokens, private keys, sensitive account details, client confidential information, or unnecessary personal data into memory files.

Load `.memory-seed/skills/memory_hygiene.md` for private/public risk distinctions, reusable-template hygiene, and redaction workflow.

## Session Log Format

Session entries use dated files under `.memory-seed/sessions/`. Entries must include the current-time heading and YAML metadata fields needed for auditability: `entry_id`, `user_initials`, `agent_type`, `project_path`, and `subproject_path`; include `agent_name` when a persona is active and `related_entries` when meaningful prior entries are linked.

Keep entries concise, reason-aware, and append-only. Load `.memory-seed/skills/session_logging.md` for the full schema, DRAFT decision record, examples, repair rules, and the local-identity/session-layout model.

Identity is opt-in and decoupled from layout: a configured local user always stamps `user_initials`, but the session log only fragments into per-user files once `.memory-seed/project.yaml` registers 2+ participants — a lone configured user stays on the shared flat file. If no local identity is configured, the SessionStart hook offers once to set one up (skippable, never repeats); `doctor` separately flags a configured user with no matching `participants:` entry.

Detailed work logs belong in the nearest active runtime. Do not mirror sub-project logs into root memory.
## Archive Policy

Archive prior control-plane snapshots under `.memory-seed/archive/<version>/` before replacing reusable versioned artifacts. Archive snapshots are historical records and may preserve old path names.

## Legacy Boundary

`.AGENTS/` is legacy-only in v2. Runtime discovery may fall back to `.AGENTS/` for older projects, but new Memory Seed projects should use `.memory-seed/`.

## Bootstrap Boundary

Do not read or apply `.memory-seed/project-bootstrap.md` during operating mode except when the active runtime is missing, incomplete, seed-only, damaged, or explicitly being bootstrapped or repaired.

If the user asks to bootstrap another project, apply bootstrap to that target project or sub-project path, not to the current initialized repository by accident. Confirm the target path when it is ambiguous.
