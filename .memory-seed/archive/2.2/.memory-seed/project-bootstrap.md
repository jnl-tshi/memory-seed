---
memory-system-version: 2.2
tags:
  - memory-seed
  - project-bootstrap
---

# Project Bootstrap And Repair Guide

This file is only for initializing a brand-new `.memory-seed/` runtime or repairing an incomplete one.

Do not read or apply this file during normal operating mode when `.memory-seed/agent-rules.md`, `.memory-seed/index.md`, `.memory-seed/policy.md`, `.memory-seed/skills/`, `.memory-seed/sessions/`, and `.memory-seed/archive/` already exist.

After `memory-seed init`, a project is expected to have reusable control files but no project-specific `index.md` or `policy.md`. That is a seeded, unbootstrapped state. Bootstrap is the procedure that creates those files from local evidence and user answers.

## When This File Applies

Use this file when:

- A target project has no `.memory-seed/` runtime.
- A target project has a partial or damaged `.memory-seed/` runtime.
- A sub-project folder needs its own isolated local runtime.
- A legacy `.AGENTS/` project is being migrated to `.memory-seed/`.

## Bootstrap Goal

Create a minimal runtime that lets future agents understand:

- where the active memory boundary is
- what the project or sub-project is
- what active state matters now
- what behavior is constrained by policy
- which runbooks are available as lazy-loaded skills
- where chronological session memory is recorded
- where prior control-plane snapshots are archived

## Required Runtime

The reusable seed installed by `memory-seed init` is:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.memory-seed/
  agent-rules.md
  project-bootstrap.md
  skills/
    index.md
    code_search.md
    data_architecture.md
    local_compilation.md
    memory_consolidation.md
    memory_doctor.md
    release_publishing.md
    security_triage.md
  sessions/
  archive/
```

Bootstrap is incomplete until these generated files also exist:

```text
.memory-seed/index.md
.memory-seed/policy.md
.memory-seed/sessions/YYYY-MM-DD.md
```

Sub-project runtimes do not need their own root `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` unless the sub-project is meant to be opened independently as a repository.

## Template Hygiene

- YAML tags in newly created files must come from the target project name, project type, and file role.
- Do not copy source-project facts, paths, model names, stack assumptions, risks, or workflow details into the target runtime.
- Reuse the memory structure and process, not the source project's domain content.
- Keep the memory core usable by file-reading AI coding agents: plain Markdown, predictable paths, explicit read order, and minimal vendor-specific assumptions.
- Tool-specific routing files should route into `AGENTS.md` and the nearest `.memory-seed/` runtime.
- Treat generated memory files as potentially publishable unless the user explicitly says the target repository will remain private.
- Never seed secrets, credentials, tokens, private keys, sensitive account details, client confidential information, or unnecessary personal data.

## Version Policy

`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and reusable files under `.memory-seed/` must share the same `memory-system-version` when they define one.

When the standard baseline changes:

- Update `memory-system-version` only when control-plane behavior changes materially.
- Keep reusable control-plane files aligned to the same version.
- Before replacing reusable versioned artifacts, archive the previous versions under `.memory-seed/archive/<version>/`.
- Record the change in `.memory-seed/sessions/YYYY-MM-DD.md`.
- Do not change the version for ordinary project-specific `index.md`, `policy.md`, skill, or session updates unless they are part of a control-plane release.

## Step 1: Inspect Local Evidence

Before asking questions, inspect:

- folder and file names
- README or docs
- dependency files
- source folders
- test folders
- data or notebook folders
- deployment files
- existing memory files
- signs that this folder is a sub-project
- current routing files
- existing conventions

If the folder is empty or ambiguous, ask targeted bootstrap questions.

## Step 2: Ask Bootstrap Questions

Ask only questions that materially change `index.md` or `policy.md`. Prefer no more than seven. Ask after local inspection, not before.

Useful questions:

1. What type of project or sub-project is this: data science/ML, production app/API, website, library/package, writing/diary/second brain, research notes, automation script, or something else?
2. Is this intended for production, public release, internal use, private/local use only, or exploratory work?
3. Does it contain sensitive data, user data, credentials, payments, personal notes, or proprietary business data?
4. What outputs matter most: code quality, reproducible analysis, polished writing, visualization, deployment reliability, fast iteration, or knowledge capture?
5. What current priority should future agents preserve across sessions?
6. Are there local conventions, workflows, or files that are easy for a new agent to miss?
7. Should this runtime inherit parent policy and skills, and which local skills should override parent skills?

If local evidence and the user request already answer these, proceed without asking.

## Step 3: Classify The Runtime

Record rich project orientation in `.memory-seed/index.md`. It must be detailed enough for a new LLM session to situate itself without reading archives.

Include:

- project purpose and durable description
- fast orientation and read order
- current state and active priority
- project or sub-project type, intended use, primary audience, and main outputs
- risk and sensitivity profile
- important source, docs, test, data, deployment, and artifact paths
- folder topology and generated/runtime files
- key workflows for development, validation, release, or writing
- current design decisions and known constraints
- active risks, open gaps, or likely wrong assumptions
- known nested runtimes
- inheritance rules for policy and skills
- active local skills, inherited parent skills, and disabled/unneeded skills
- skill trigger registry expectations, including `.memory-seed/skills/index.md` in `Always Read` and `Lazy Skills`
- MCP history retrieval expectations, including `memory_search`, `memory_get_chunk`, entry granularity by default, section granularity for narrow searches, and direct session-file fallback when MCP is unavailable
- session memory location and promotion guidance

Record durable behavioral constraints in `.memory-seed/policy.md`, not in `index.md`.

## Step 4: Create Or Repair Routing Files

Create root `AGENTS.md` as the generic entry point if it does not already exist. It should route agents to nearest `.memory-seed/` discovery.

Create `CLAUDE.md` and `GEMINI.md` if the project needs those tool-specific routing files. They should point back to `AGENTS.md` and not define independent memory systems.

## Step 5: Create Or Repair Runtime Files

Create or repair:

- `.memory-seed/agent-rules.md`: operating workflow.
- `.memory-seed/project-bootstrap.md`: this bootstrap and repair workflow.
- `.memory-seed/index.md`: generated project orientation, durable context, topology, active state, inheritance, and skill pointers.
- `.memory-seed/policy.md`: generated behavioral constraints.
- `.memory-seed/skills/index.md`: deterministic trigger registry.
- `.memory-seed/skills/*.md`: reusable runbooks.
- `.memory-seed/sessions/YYYY-MM-DD.md`: first session log.
- `.memory-seed/archive/`: archive directory.

Do not copy source-project domain facts into the target runtime.

## Step 6: Write index.md

Minimum sections:

```markdown
# Memory Seed Runtime Index

## Purpose
## Fast Orientation
## Current State
## Project Type And Risk
## Audience And Outputs
## Runtime Boundary
## Inheritance
## Always Read
## Lazy Skills
## Active State
## Topology
## Workflows
## Design Decisions
## Risks And Open Questions
## Session Memory
```

Keep it concise but substantive. It is not a raw history, but it should carry enough durable context for a new agent to understand what the project is, what matters now, how to navigate it, and which mistakes to avoid.

Use enough situating detail for a new agent to understand the project purpose, current state, important paths, workflows, risks, and active decisions without relying on historical context.

## Step 7: Write policy.md

Minimum sections:

```markdown
# Memory Seed Runtime Policy

## Scope
## Global Behavior
## Safety
## File Ownership
## Security And Privacy
## Sub-Projects
## End Of Work
```

Security must be proportional:

- Production-facing, public, networked, or user-data projects require explicit security best practices.
- Private local knowledge projects require privacy and backup guidance, not unnecessary production process.
- If uncertain, protect secrets, credentials, personal data, and destructive operations by default.

## Step 8: Create Skills

The seed may provide generic skill templates, but bootstrap decides which skills are active for this project.

Consider the default skill set:

- `security_triage.md`
- `index.md`
- `data_architecture.md`
- `local_compilation.md`
- `code_search.md`
- `memory_consolidation.md`
- `memory_doctor.md`
- `release_publishing.md`

For code projects, include `code_search.md` and prefer Semble before grep/full-file reads. If `semble` is not on `PATH`, use `uvx --from "semble[mcp]" semble`.

For sub-projects, inherit parent skills by default and create local skill files only when the sub-project needs an override or a genuinely local runbook. Record local, inherited, and disabled skills in `index.md`.

Always include `skills/index.md` as the deterministic trigger registry for universal skills. Generated `index.md` should reference it in `Always Read` and `Lazy Skills` so agents can decide which full skill runbooks to load without preloading all skills.

For project-specific execution patterns, create a local skill instead of expanding `agent-rules.md` or `policy.md`.

## Step 9: Create First Session Log

Create `.memory-seed/sessions/YYYY-MM-DD.md` with file frontmatter:

```yaml
---
tags:
  - session-log
  - memory-seed
session_date: YYYY-MM-DD
---
```

For each entry, use a timestamped heading followed by entry metadata:

````markdown
## YYYY-MM-DD HH:MM - Short title

```yaml
entry_id: ms-8charhash
user_initials: USER
agent_type: codex
project_path: .
subproject_path: null
```
````

Generate `entry_id` as a deterministic short hash from metadata only: timestamp, title, user initials, agent type, project path, and subproject path. Do not hash the entry body.

Record the bootstrap entry using DRAFT decision records in the meaningful decision or multi-decision shape from `.memory-seed/agent-rules.md`.

Include:

- bootstrap date
- project classification
- questions asked and answers received
- files created
- assumptions
- inheritance choices
- follow-up gaps

Record reason for bootstrap choices that shape future behavior:

- project classification
- policy and risk posture
- inheritance model
- active skill selection
- major assumptions

Do not require reason for obvious file discoveries. Do not invent reason; mark inferred reason explicitly or write `Reason not recorded` when unknown.

Keep sessions append-only.

## Step 10: Validate Bootstrap

Bootstrap is incomplete until all checks pass:

- `AGENTS.md` exists and routes agents to nearest `.memory-seed/`.
- Optional tool-specific routing files point back to `AGENTS.md`.
- `.memory-seed/agent-rules.md` exists and defines operating-mode rules.
- `.memory-seed/project-bootstrap.md` exists and is marked bootstrap/repair only.
- `.memory-seed/index.md` contains enough project purpose, current state, topology, risk, workflows, design decisions, inheritance, and skill context for a new LLM session to situate itself.
- `.memory-seed/policy.md` contains behavioral constraints only.
- `.memory-seed/skills/index.md` contains the deterministic skill trigger registry.
- `.memory-seed/skills/` contains runbooks only, not active state.
- `.memory-seed/sessions/YYYY-MM-DD.md` records bootstrap decisions.
- `.memory-seed/archive/` exists.
- No stale `.AGENTS/` paths are presented as canonical.
- Security posture matches risk level.
- `index.md` is enough for project traversal without guessing.

After validation, switch to operating mode and stop using this file.
