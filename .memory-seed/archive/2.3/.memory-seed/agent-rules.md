---
memory-system-version: 2.3
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

Ask the user before creating a nested runtime unless they explicitly requested sub-project memory setup. When approved or requested:

1. Confirm the target sub-project path.
2. Run Memory Seed initialization from that target path.
3. Bootstrap the sub-project from local evidence and targeted user answers.
4. Record local inheritance choices in the sub-project `index.md`.
5. Record the nested runtime's existence and purpose in the parent or root `index.md`.

Sub-project runtimes do not need their own root `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` unless the sub-project is meant to be opened independently as a repository.

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
7. Read `.memory-seed/skills/index.md` as the deterministic skill trigger registry.
8. Load full `.memory-seed/skills/*.md` runbooks only when the trigger registry matches the current task.

Do not read or apply `.memory-seed/project-bootstrap.md` during normal operating mode unless the runtime is missing or incomplete.

## History Retrieval And Conflict Resolution

Use MCP history retrieval when prior decisions, reason, unresolved risks, architecture, policy, bootstrap behavior, release history, or "why was this done" matters. This is a quick-start for agents that can call MCP tools.

### When To Search

Call `memory_search` before relying on the visible conversation alone when the task asks about or depends on:

- a past design decision, architecture choice, policy change, bootstrap choice, release, migration, or unresolved risk
- why a file, workflow, or memory structure behaves a certain way
- whether a current request conflicts with older session history
- sub-project boundaries, inherited policy, or prior agent handoff context

Skip MCP history lookup for small, obvious edits where current source files and the active `index.md` / `policy.md` are enough.

### Tool Mechanics

The MCP server exposes two tools:

- `memory_search`: ranks session-memory entries or sections.
- `memory_get_chunk`: fetches the full text for one returned `chunk_id`.

Default search payload:

```json
{
  "query": "short natural-language description of what you need to know",
  "cwd": ".",
  "top_k": 5,
  "granularity": "entry"
}
```

Use `cwd` as the project or sub-project path you are operating in. The runtime resolver uses the nearest `.memory-seed/` directory from that path.

Use `granularity: "entry"` by default. It returns one coherent chunk for each `##` session entry, and `chunk_id` is normally the entry YAML `entry_id`, such as `ms-db2d715c`.

Use `granularity: "section"` only when entries are long, multi-topic, or the task needs narrower targeting. Section chunk ids append a heading path to the parent entry id, such as `ms-db2d715c#decisions/d1-use-draft-for-compact-decision-records`.

Useful optional search fields:

```json
{
  "semantic_enabled": true,
  "recency_enabled": true,
  "recency_floor": 0.15
}
```

Recency is anchored to the current date read from the system clock at call time. There is no date-override field; the tool never trusts a caller-supplied "today".

If semantic scoring is unavailable, the tool falls back to lexical, metadata, and recency ranking. Do not treat semantic fallback as a failure unless the task requires semantic search specifically.

Search results include `chunk_id`, `entry_id`, `source`, `line_range`, `heading_path`, `excerpt`, matched fields, score fields, entry metadata, and `granularity`. Treat excerpts as previews only.

Fetch any result that may affect implementation, policy, bootstrap behavior, release behavior, or memory structure:

```json
{
  "chunk_id": "ms-db2d715c",
  "cwd": "."
}
```

Use the fetched chunk text, not just the excerpt, when making or evaluating a consequential decision.

If MCP tools are unavailable, read recent and relevant `.memory-seed/sessions/YYYY-MM-DD.md` files directly. Start with the last two session files, then search older dated files by keyword if needed. Apply the same authority and conflict rules below.

Current files are the active authority: `.memory-seed/index.md`, `.memory-seed/policy.md`, active `.memory-seed/skills/*.md`, and source/config files for implementation truth. Session history is evidence and reason, not automatic authority.

When history conflicts with current authority files, resolve by timeline only when all clear supersession criteria are met:

- the superseding source is a newer dated session entry or current authority file
- it states an explicit decision boundary
- it names the affected files, behavior, policy, or design area
- no later reversal or unresolved disagreement is found

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
- `.memory-seed/sessions/YYYY-MM-DD.md`: append-only chronological work history.
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

- `.memory-seed/sessions/YYYY-MM-DD.md`: append concise notes after meaningful work, before the current turn ends.

Do not rewrite old session entries unless the user explicitly asks for repair, archival cleanup, or correction.

## End Of Turn

This rule applies to all agents equally — Claude, Codex, Gemini, and any other agent reading these instructions.

After any turn where meaningful work was completed:

1. **Append a concise note to `.memory-seed/sessions/YYYY-MM-DD.md` before this turn ends.** Do not defer it to the next turn. Do not batch multiple turns into one entry later. Write it now.
2. Review whether `.memory-seed/index.md` needs updated topology, active state, inheritance, or skill pointers.
3. Review whether `.memory-seed/policy.md` needs durable behavioral-policy changes.
4. Review whether any `.memory-seed/skills/*.md` runbook changed.
5. If work occurred in a sub-project runtime, review whether the parent or root runtime needs a brief coordination summary.
6. Run the smallest verification that proves the work.

Deferring or batching session log writes is a discipline failure, not an acceptable workflow. If the current turn produced anything worth remembering — a decision, a file change, a resolved blocker, a tradeoff — write it now.

### Append-Only Chronology

The session file is strictly append-only and must stay in ascending time order. To guarantee this without ever reordering:

- Append every new entry to the **end** of the day's file. Never insert an entry above an existing one.
- **Append each entry at the physical end of the file; never insert above an existing entry.** That is the rule; the mechanism is up to your tools. The common failure is anchor-based edit tools — if you target a line you wrote earlier, a later edit may already sit below it, so the new entry lands mid-file. Avoid it by confirming the *actual* last line immediately before appending (for example, read the file's tail); never reuse an anchor from memory. With a POSIX shell or Python, append mode (`>> file`, `open(f, 'a')`) sidesteps anchors entirely — write UTF-8 (some shells, for example PowerShell `>>`, default to other encodings).
- The entry heading timestamp is the **actual current clock time** at the moment you write it. Read it from the system clock; never reuse a time from your context, memory, or an earlier message, and never backdate it to when the work happened.
- Because entries are always appended with the current time, file order, write order, and timestamp order are identical. No manual reordering is ever needed or allowed.
- If you are recording work that completed earlier in the session (you forgot, or you are catching up), still stamp the heading with the current time. If the original work time matters, state it in the entry body — do not move the entry above newer ones and do not rewrite earlier headings.

This is the invariant the "do not rewrite old session entries" rule protects: out-of-order or backdated entries force a human to manually re-sort the log, which is exactly what append-only is meant to prevent. Confirming the real last line before each append — or using append mode where your environment supports it — makes this invariant mechanical rather than reliant on a remembered anchor.

Detailed work logs belong in the nearest active runtime. Add a parent/root summary only when sub-project work changes parent-visible topology, shared design, release behavior, policy inheritance, cross-project dependencies, risks, or active priorities. Do not mirror sub-project logs into root memory.

Session entries must capture reason when it matters, without forcing ceremony for small work. Use reason for durable decisions, architecture changes, policy changes, bootstrap choices, release decisions, non-obvious tradeoffs, or changes likely to confuse a future agent.

## Consolidation Review Triggers

Review recent session logs for durable-memory promotion when any of these are true:

- More than three meaningful session entries have accumulated since last consolidation.
- A completed task changed project direction, architecture, release process, CLI behavior, workflow rules, file ownership, or durable risk.
- A session produced more than roughly 2,000 words / 8,000 tokens of notes or compact output.
- A release, publish, migration, bootstrap repair, security decision, or major refactor completed.
- `index.md`, `policy.md`, or a skill no longer reflects current project state.

These triggers require review, not automatic edits. Promote only facts that are stable, reusable, and likely to help a future agent avoid wrong assumptions.

Use `.memory-seed/skills/memory_consolidation.md` for the detailed compact-and-promote workflow.

## Skill Loading

Skills are lazy-loaded runbooks. Read `.memory-seed/skills/index.md` first as the one-stop deterministic trigger registry. Load full skill runbooks only when the registry matches the task.

- `index.md`: deterministic trigger registry; read during startup before loading full skills.
- `code_search.md`: searching source code or repo structure efficiently.
- `data_architecture.md`: changing durable data structures, indexes, schemas, or retrieval behavior.
- `local_compilation.md`: validating local build/test/package/run behavior.
- `memory_consolidation.md`: compacting session memory and promoting durable facts.
- `memory_doctor.md`: validating runtime health and migration integrity.
- `release_publishing.md`: preparing or publishing package releases.
- `security_triage.md`: reviewing security-sensitive changes.

Evaluate registry rules in listed order, load every matching required skill, and keep the loaded set as small as the task safely allows. For sub-projects, use the nearest runtime's registry first; inherited parent registries apply only when enabled and not locally overridden or disabled.

### Code Search Trigger

For code search, repository exploration, symbol lookup, or broad codebase orientation, load `.memory-seed/skills/code_search.md` before broad grep sweeps or full-file reads. Prefer the skill's search hierarchy for software, library, API, and tooling projects.

### Memory Doctor Trigger

Load `.memory-seed/skills/memory_doctor.md` when runtime health, migration integrity, missing files, archive state, seed/live sync, or bootstrap completion is uncertain. Use it before repairing memory structure unless the problem is already obvious and narrow.

### Compact And Consolidation Trigger

Load `.memory-seed/skills/memory_consolidation.md` when reviewing compact output, promoting durable memory, reconciling session history with `index.md` / `policy.md`, or deciding whether long session logs need summarizing. Compact output is review input, not an automatic write plan.

## Public Memory Hygiene

Treat `.memory-seed` files as potentially publishable unless the user explicitly says the repository will always remain private.

Do not write secrets, credentials, tokens, private keys, sensitive account details, client confidential information, or unnecessary personal data into `index.md`, `policy.md`, skills, archive notes, or session logs.

When a project may become public, keep session entries focused on durable technical decisions and omit private local paths, private identities, and sensitive operational details unless the user explicitly asks to preserve them.

Reusable seed files must stay generic. Do not write project-specific private paths, identities, account details, or domain facts into `memory_seed/seed/` templates.

## Session Log Format

Use dated files under `.memory-seed/sessions/` with file-level frontmatter:

````markdown
---
tags:
  - session-log
  - memory-seed
session_date: 2026-05-02
---

## 2026-05-02 14:35 - Project setup and workflow update

```yaml
entry_id: ms-8charhash
user_initials: USER
agent_type: codex
project_path: .
subproject_path: null
```

### Summary

- Updated the project workflow or implementation area touched today.

### Validation

- Ran the smallest relevant verification.

### Follow-up

- Note any rerun, review, or unresolved risk.
````

Keep session filenames date-only, such as `.memory-seed/sessions/2026-05-02.md`. Use minute-level timestamps in entry headings, taken from the current system clock at write time. Entries are appended in clock order and never backdated or reordered (see Append-Only Chronology). Generate `entry_id` as a deterministic short hash from metadata only: timestamp, title, user initials, agent type, project path, and subproject path. Use known user initials when available; otherwise ask during bootstrap or use a neutral placeholder until confirmed. Capture meaningful decisions, durable changes, follow-up risk, or handoff context. Do not log every command.

### Reason Rules

**DRAFT** is the compact decision-record format used inside session entries. Use it whenever a meaningful decision was made or implemented.

A DRAFT decision record uses compact labels:

- D = Decision — what was chosen
- R = Reason — the decisive reason, 1–3 bullets; **required**
- A = Alternatives considered or rejected, with reason (optional unless it shaped the tradeoff)
- F = Files, artifacts, or behaviors changed (optional)
- T = Tests or validation outcome (optional; may appear inline as `- T:` or as a separate `### Validation` section)

`D` and `R` are required for every meaningful decision. `A`, `F`, and `T` are optional when not relevant.

- Do not invent reason.
- If reason is inferred, label it `Inferred reason`.
- If reason is unknown, write `Reason not recorded`.
- Alternatives are optional unless they affected the decision or tradeoff.
- Use `D1`, `D2`, and similar labels only inside a multi-decision entry; `entry_id` is the global reference.
- Do not rewrite old logs solely to match the newest schema unless the user explicitly asks.

### Entry Shapes

Use the lightest entry shape that preserves future usefulness.

#### Small work entry

Use for routine edits, small fixes, or verification-only work.

```markdown
### Summary

- What changed or what was checked.

### Validation

- Command or check and outcome, if relevant.

### Follow-up

- Only include if there is residual risk or a next action.
```

#### Meaningful decision entry

Use when one durable decision was made or implemented.

```markdown
### Decision

- D: State the decision.
- R: Explain the decisive reason in 1-3 bullets.
- A: Alternative considered or rejected, with reason, if it mattered.
- F: Files, artifacts, or behaviors changed.
- T: Tests or validation outcome.
```

#### Multi-decision session entry

Use one entry when several decisions belong to one coherent task, plan, or user goal. Split entries when decisions affect unrelated subsystems, sub-projects, or goals.

```markdown
### Summary

- Summarize the coherent task.

### Decisions

#### D1 - Short decision name

- D: State the choice.
- R: Explain the decisive reason in 1-3 bullets.
- A: Alternative considered or rejected, with reason, if it mattered.
- F: Files, artifacts, or behaviors changed.
- T: Tests or validation outcome.

#### D2 - Short decision name

- D: State the choice.
- R: Explain the decisive reason in 1-3 bullets.

### Implementation

- Summarize changed behavior, not every file.

### Validation

- Commands or checks and outcomes, not full output.

### Follow-up

- Residual risks or next actions.
```

## Archive Policy

Archive prior control-plane snapshots under `.memory-seed/archive/<version>/` before replacing reusable versioned artifacts. Archive snapshots are historical records and may preserve old path names.

## Legacy Boundary

`.AGENTS/` is legacy-only in v2. Runtime discovery may fall back to `.AGENTS/` for older projects, but new Memory Seed projects should use `.memory-seed/`.

## Bootstrap Boundary

Do not read or apply `.memory-seed/project-bootstrap.md` during operating mode except when the active runtime is missing, incomplete, seed-only, damaged, or explicitly being bootstrapped or repaired.

If the user asks to bootstrap another project, apply bootstrap to that target project or sub-project path, not to the current initialized repository by accident. Confirm the target path when it is ambiguous.
