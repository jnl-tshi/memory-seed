---
memory-system-version: 2.20
tags:
  - memory-seed
  - agent-rules
  - operating-mode
---

# Agent Rules

These rules define the non-deferrable startup contract for how AI agents use the nearest `.memory-seed/` runtime. Keep procedural details in skills and leave `agent-rules.md` focused on discovery, authority, safety gates, and lazy-skill routing.

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
4. Read `.memory-seed/skills/orientation.md`. Use the SessionStart hook's shared `situate` facts, or run
   `memory-seed situate` when they are absent or stale.
5. Apply the measured latest-session route: read the whole file directly at or below 12,000 characters;
   above that boundary, use the skill's read-only economy-worker compression contract. Never use
   `memory_search` to determine what is latest. On the **first substantive message**, once intent is
   known, run the skill's operating-mode gate.
6. Once intent is known: Read `.memory-seed/skills/index.md` as the deterministic skill trigger registry and load only matching runbooks.
7. Read `.memory-seed/index.md` sections when the task depends on topology, authority, inheritance,
   active state, or project-wide priorities.
8. Read inherited and active `.memory-seed/policy.md` before writes or when behavioral constraints matter.
9. Before consequential design, governance, or control-plane work, if the active index declares a ratified Constitution,
   read it. Once the concern is known, run `memory-seed adr list --json` and read only relevant
   accepted/proposed heads. Do not preload the whole ADR corpus.
10. If `.agents/_registry.yaml` exists, load active personas only after intent makes their relevance known.
    **Primary agents only:** a spawned worker follows the Worker Context Contract — packet + at most one
    persona + packet-triggered skills, skipping steps 4–10 while retaining `base_sha`/preflight and the
    worktree guard. Its packet must name any policy, Constitution, or ADR context the objective requires.

Load full `.memory-seed/skills/*.md` runbooks only when the trigger registry matches the current task.

When multiple personas are active, the one most relevant to the current task governs. Default to the first active entry in `_registry.yaml` when ambiguous.

Do not read or apply `.memory-seed/project-bootstrap.md` during normal operating mode unless the runtime is missing or incomplete.

## History Retrieval And Conflict Resolution

Use MCP history retrieval when prior decisions, reason, unresolved risks, architecture, policy, bootstrap behavior, release history, or "why was this done" matters. Load `.memory-seed/skills/history_retrieval.md` for retrieval mechanics, `memory_search` and `memory_get_chunk` payloads, result interpretation, direct-file fallback, and conflict handling.

### Recency vs. Topical Retrieval

Newest-state questions use the SessionStart/`situate` route selected from the latest session file by date.
Topical questions use `memory_search`, with consequential results fetched by `memory_get_chunk`. These
are different workflows and should not be substituted for each other.

Resolve authority in this order: a declared ratified Constitution; the current control file that owns
the concern; accepted ADR heads; session evidence; derived projections. The index routes and
summarizes; policy states executable constraints; ADRs own durable decision rationale and evolution.
Proposed ADRs and draft Constitutions are evidence, not governing authority. Source/config files
remain implementation truth, and session history remains evidence and reason rather than automatic
authority.

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

- Level 0: direct, simple, low-risk work.
- Level 1: inspect, implement, and run targeted verification.
- Level 2: orchestrator, bounded workers, and validator for large, multi-file, ambiguous, risky, or parallelizable work.
- Level 3: research and human checkpoints for architecture, security, release, destructive, or changing-best-practice decisions.

Default to the least expensive level and smallest context set that can safely handle the task. Load `.memory-seed/skills/agent_collaboration.md` for the detailed workflow, including subagents, branch/worktree coordination, task packets, capability tiers, review loops, and merge handoffs. Load `.memory-seed/skills/risk_signaling.md` for STOP categories before ambiguous, destructive, irreversible, security-sensitive, externally visible, financial, or shared-control-plane actions.

## File Ownership

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`: routing files.
- `.memory-seed/agent-rules.md`: operating workflow and memory ownership rules.
- `.memory-seed/project-bootstrap.md`: bootstrap and repair procedure.
- `.memory-seed/index.md`: rich project orientation, current state, topology, inheritance, and skill pointers.
- `.memory-seed/policy.md`: behavioral constraints only.
- `.memory-seed/decisions/*.md`: append-only durable concern decisions, rationale, and evolution.
- A Constitution, only when its path and ratified status are declared by the active index: the
  normative ceiling for lower control-plane documents.
- `.memory-seed/skills/*.md`: task-specific runbooks, loaded on demand.
- `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` or `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD/<user>.md`: append-only chronological work history.
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

Immediate durable-memory update exception: update `.memory-seed/index.md`, `.memory-seed/policy.md`, or an active skill during a session only when leaving the current content stale would immediately mislead active work, route an agent to wrong files, preserve an unsafe assumption, or cause repeated incorrect actions. This includes recording a durable fact established this turn that has no entry to live in (see `session_logging.md`'s Decision Harvest) — an `index.md` that never gained the fact is exactly as misleading as one that kept a stale one.

For restricted files, the agent must be able to explain why the file's ownership scope was affected.

Routine append:

- Append concise notes after meaningful work, before the current turn ends. Canonical path:
  `memory-seed session append` (enforces target, chronology, canonical `entry_id`, ref/topic
  validity, branch capture; body prose passes through verbatim). Composing by hand: resolve the
  target with `memory-seed session target`, compute the id with `session entry-id` - never invent it.

Do not rewrite old session entries unless the user explicitly asks for repair, archival cleanup, or correction.

## Working Principles

Cross-cutting principles that apply to any agent and any task:

- Prove risky or hard-to-verify automation on a small case before applying it broadly.
- State what the agent verified versus what only the user can verify.
- Before adding code, check whether it needs to exist, already exists, or is already covered by stdlib/platform behavior; likewise, before a consequential review, recommendation, design, or change decision on non-obvious behavior, retrieve the prior reasoning first (`memory_search` for "why was X / what was tried", then fetch the relevant entry) to inherit rejected alternatives, constraints, deferred items, and landmines rather than re-deriving them — files are authority for what is true now, memory is authority for why, never substitute one for the other.
- Do not remove terse guards without understanding what they protect.
- Default to plain text for ordinary explanations; when a session decision has spatial, temporal, topology, migration, compatibility, or concurrent structure, follow the decision-diagram sidecar triggers in `session_logging.md` and load `compact_mermaid_diagrams.md` before authoring Mermaid.
- Commits link to their session entries via `Memory-Entry: <entry_id>` trailers. The seeded `prepare-commit-msg` git hook stamps them automatically for staged session entries (`memory-seed hooks install` if not yet installed), and `session merge-branch` stamps its own on merge commits; hand-write a trailer only when linking a commit to a motivating entry the diff does not contain.
- A branch is a **workstream, not a single commit**: batch follow-on fixes, evolutions, and adjacent tweaks of the same goal onto the SAME branch — the tell is an `evolves`/`related` lifecycle edge to the entry you just wrote, or the same files/area — and merge the batch into the base at a stable, tested stopping point, not after every commit. Open a NEW branch only for a genuinely new, independent goal. Preserve visible branch history for distinct workstreams by loading `agent_collaboration.md` before editing and using a task branch/worktree unless the user chooses another history model; for branch/worktree write work, run its agent-namespace guard preflight first.
- Use qualitative risk tiers before acting by loading `.memory-seed/skills/risk_signaling.md` for ambiguous, destructive, irreversible, externally visible, financial, security-sensitive, or shared-control-plane work.
- Load `.memory-seed/skills/skill_architecture.md` before adding, removing, renaming, splitting, or refactoring skills, editing `skills/index.md`, changing profiles, or moving procedural guidance between this file, `policy.md`, and skills.
- Before integration, read `.memory-seed/project.yaml` `integration_mode`: unset/`local-merge` runs `session integrate` or `merge-branch` from the integration/base checkout and never pushes; `pr` runs `session integrate` or `open-pr` from the task branch, where only the declared mode authorizes a normal non-force push and PR. A Task Packet's `integration_artifact` overrides the default; force and other destructive operations remain gated. **No hook checks this either** — misreading it risks an unwanted push or PR, so re-read the mode immediately before the integration step itself, not from memory of an earlier turn.
## End Of Turn
After any turn where meaningful work was completed, append a concise entry to the active session target before the turn ends. Deferring or batching session log writes is a discipline failure. A prior session's choice not to log or not to act on something is scoped to exactly what it named, not blanket precedent for later turns — logging your own turn's changes is required regardless of what else is already dirty or what an earlier entry said about it (measured 2026-08-31: a session's own note excusing itself from logging pre-existing dirty files was apparently read as covering unrelated later work too, and the two sessions with real code changes stopped logging). Writing a change into the affected file is not itself a memory record — files are authority for what is true now, memory is authority for why and when (see the Working Principles entry below); a turn that only writes a fact directly into a project file still owes at minimum a small-work entry.

Start with `memory-seed esr` - one read-only report covering the mechanical checks (links, topics, session-scoped link audit, worktree posture, seed-twin drift). Then load `.memory-seed/skills/end_of_turn.md` for the full ESR checklist: session entry, lifecycle link sweep, consolidation review, policy/index/skill review, verification, orphan and artifact sweep, stale worktree sweep, persona evolution, skill evolution, unregistered persona check, and baseline-promotion review.

Load `.memory-seed/skills/session_logging.md` for session frontmatter, entry YAML, DRAFT labels, entry shapes, append-only chronology, `related_entries`, and examples.

### Consolidation Review Triggers

Review recent session logs for durable-memory promotion when meaningful session volume, project direction, release behavior, policy, architecture, migration, bootstrap repair, security posture, or reusable workflow state has changed. Use `.memory-seed/skills/memory_consolidation.md` for the detailed compact-and-promote workflow.

These triggers require review, not automatic edits. Promote stable conclusions, not full decision history.

## Skill Loading

Skills are lazy-loaded runbooks. `index.md`: deterministic trigger registry — read `.memory-seed/skills/index.md` first, the authoritative `load_when`/`do_not_load_when` map for every skill; this section is a pointer to it, not a second copy. Two are worth knowing by name because nearly every turn needs them: `session_logging.md` (session entry shape, DRAFT labels, `related_entries`) and `end_of_turn.md` (the closeout obligation below, full ESR checklist). Every other skill routes through the registry as normal — load only what a `load_when` rule actually matches.

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

Session entries use dated files under `.memory-seed/sessions/`. Entries include a current-time heading plus YAML fields for auditability: `entry_id`, `user_initials`, `agent_type`, `project_path`, and `subproject_path`; include `related_entries` when meaningful prior entries are linked.

Keep entries concise, reason-aware, and append-only. Load `.memory-seed/skills/session_logging.md` for the full schema, DRAFT decision record, branch/commit/supersession fields, examples, repair rules, and the local-identity/session-layout model.

Detailed work logs belong in the nearest active runtime. Do not mirror sub-project logs into root memory.

## Archive Policy

Archive prior control-plane snapshots under `.memory-seed/archive/<version>/` before replacing reusable versioned artifacts. Archive snapshots are historical records and may preserve old path names.

## Legacy Boundary

`.AGENTS/` is legacy-only in v2. Runtime discovery may fall back to `.AGENTS/` for older projects, but new Memory Seed projects should use `.memory-seed/`.

## Bootstrap Boundary

Do not read or apply `.memory-seed/project-bootstrap.md` during operating mode except when the active runtime is missing, incomplete, seed-only, damaged, or explicitly being bootstrapped or repaired.

If the user asks to bootstrap another project, apply bootstrap to that target project or sub-project path, not to the current initialized repository by accident. Confirm the target path when it is ambiguous.
