---
memory-system-version: 1.4
tags:
  - ai-memory
  - project-bootstrap
---

# Project Bootstrap Guide

This file is only for initializing a brand-new project or repairing an incomplete `.AGENTS` folder.

Do not read or apply this file during normal operating mode. If `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and `.AGENTS/sessions/` already exist, use `.AGENTS/agent-rules.md` and `.AGENTS/index.md` instead.

## When This File Applies

Use this file only when the project is empty or the target project is still at the reusable seed state:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.AGENTS/
  agent-rules.md
  project-bootstrap.md
```

Once `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and `.AGENTS/sessions/` exist, bootstrap mode is complete and future sessions should use operating mode.

## Template Hygiene

- YAML tags in newly created files must be generated from the new project name, project type, and file role. Do not copy source-project tags such as a previous repository name.
- `context.md` and `style.md` must not inherit source-project facts, paths, model names, stack assumptions, risks, or workflow details from the project where this bootstrap guide was copied from.
- Reuse the memory structure and process, not the source project's domain content.
- Keep the memory core usable by file-reading AI coding agents: plain Markdown, predictable paths, explicit read order, and minimal vendor-specific assumptions.
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.AGENTS/agent-rules.md`, and `.AGENTS/project-bootstrap.md` are reusable control-plane files. Copy the standard baseline for these files unless the user explicitly requests a different memory workflow.
- Tool-specific routing files should route into `AGENTS.md` and the shared `.AGENTS/` memory core rather than creating separate vendor memories.
- Keep the same operating/bootstrap boundary across projects so initialized projects do not drift into incompatible agent-routing structures.
- Treat generated memory files as potentially publishable unless the user explicitly says the target repository will remain private. Never seed secrets, credentials, tokens, private keys, sensitive account details, client confidential information, or unnecessary personal data into generated memory.


## Version Policy

`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.AGENTS/agent-rules.md`, and `.AGENTS/project-bootstrap.md` must share the same `memory-system-version` value because they define the reusable control plane together.

When the standard baseline changes:

- Update the shared `memory-system-version` only when the control-plane behaviour changes materially.
- Keep all reusable control-plane files aligned to the same version.
- Before replacing reusable control-plane files, archive the previous versions under `.AGENTS/archive/<version>/`.
- Record the change in `.AGENTS/sessions/YYYY-MM-DD.md` for the project where the change is made.
- Do not change the version for project-specific `context.md`, `index.md`, or `style.md` updates.

## Bootstrap Goal

Create a minimal, project-specific memory system that lets future agents understand:

- what the project is
- why it exists
- how to navigate it
- what conventions to follow
- what risks matter
- where chronological work history is recorded

## Step 1: Inspect Local Evidence

Before asking questions, inspect available project evidence:

- folder and file names
- README or notes
- dependency files
- notebooks
- source folders
- docs folders
- deployment files
- data folders
- existing conventions

If the folder is empty or ambiguous, ask targeted bootstrap questions.

## Step 2: Ask Bootstrap Questions

Ask no more than five questions. Ask only questions that materially change `context.md` or `style.md`.

Recommended questions:

1. What type of project is this: data science/ML, production app/API, website, library/package, writing/diary/second brain, research notes, automation script, or something else?
2. Is this intended for production, public release, internal use, private/local use only, or exploratory work?
3. Does it handle sensitive data, user data, credentials, payments, personal notes, or proprietary business data?
4. What outputs matter most: code quality, reproducible analysis, polished writing, visualisation, deployment reliability, fast iteration, or knowledge capture?
5. Will this project be synced, published, deployed, shared, or connected to external services?

If the user already gave enough information, proceed without asking.

## Step 3: Classify The Project

Record these fields in `.AGENTS/context.md`:

- Project type.
- Intended use.
- Primary audience.
- Risk level: private/local, internal, public, production, or regulated/sensitive.
- Security posture.
- Primary outputs.
- Expected workflow.

Use a cautious security posture when risk is unclear and the project may include secrets, credentials, personal data, user data, payments, proprietary data, network exposure, or destructive automation.

If the project may be public, record privacy constraints in `.AGENTS/context.md` and keep `.AGENTS/sessions/` entries free of sensitive details.

## Step 4: Create The Files

Create or update every required bootstrap output. Bootstrap is incomplete until all of these exist:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.AGENTS/
  agent-rules.md
  project-bootstrap.md
  index.md
  context.md
  style.md
  sessions/
    YYYY-MM-DD.md
```

Create root `AGENTS.md` as the entry point for future agents if it does not already exist.
Create root `CLAUDE.md` as the Claude Code routing file if it does not already exist.
Create root `GEMINI.md` as the Gemini CLI routing file if it does not already exist.

`AGENTS.md` should say:

- In operating mode, read `.AGENTS/agent-rules.md`, `.AGENTS/index.md`, and `.AGENTS/context.md`.
- Do not read or apply `.AGENTS/project-bootstrap.md` once `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and `.AGENTS/sessions/` exist.
- Use `.AGENTS/project-bootstrap.md` when `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, or `.AGENTS/sessions/` are missing.

`CLAUDE.md` should say:

- The canonical agent instructions for the repository are in `AGENTS.md`.
- Claude Code should open `AGENTS.md` before planning, editing, reviewing, or running commands.
- Tool-specific behavior may adapt tooling, but not policy.
- `CLAUDE.md` is a routing file, not a replacement memory system.

`GEMINI.md` should say:

- The canonical agent instructions for the repository are in `AGENTS.md`.
- Gemini CLI should open `AGENTS.md` before planning, editing, reviewing, or running commands.
- Tool-specific behavior may adapt tooling, but not policy.
- `GEMINI.md` is a routing file, not a replacement memory system.

## Step 5: Seed context.md

Minimum sections:

```markdown
# Project Context

## Purpose
## Fast Orientation
## Current State
## Project Type And Risk
## Agent Start Here
## Project Folder Structure
## Core Workflow
## Key Outputs
## Security And Privacy Notes
## Memory Rules
```

`context.md` must be enough for an agent to traverse the project without guessing.

## Step 6: Seed index.md

Keep `index.md` short:

```markdown
# Agent Memory Index

## Always Read

- `.AGENTS/agent-rules.md`
- `.AGENTS/context.md`
- `.AGENTS/style.md` when editing code, docs, or project conventions

## Historical Memory

- `.AGENTS/sessions/*.md`

## Hot Facts

- Project type:
- Current priority:
- Main output:
- Current risk:

## Bootstrap Boundary

Do not read or apply `.AGENTS/project-bootstrap.md` during operating mode.
```

## Step 7: Select Style Profile And Generate style.md

Do not copy a generic style guide. Bootstrap owns the style decision because `style.md` does not exist yet in a brand-new target project. Generate `style.md` from the classified project type, intended use, audience, outputs, workflow, and risk.

Include a short classification block:

```markdown
## Style Basis

- Project type:
- Intended use:
- Risk level:
- Why these conventions apply:
```

Select one primary style profile, then add any secondary profile needed for risk or workflow. Record the selected profile in both `context.md` and `style.md`.

Style profiles:

- Memory-system development: use when the target project develops, tests, or distributes the memory seed itself. Emphasize control-plane vs generated-file boundaries, version policy, archive rules, portability, and session-log rationale.
- Software or production project: use for apps, APIs, websites, packages, libraries, and tools. Emphasize architecture, setup commands, test commands, dependency hygiene, secure defaults, logging without sensitive data, deployment assumptions, and rollback-aware changes.
- Data science or ML: use for notebooks, experiments, model training, analysis, and data pipelines. Emphasize reproducibility, data leakage prevention, train/validation/test boundaries, experiment tracking, notebook execution order, artifact versioning, and metric discipline.
- Writing, essay, or research: use for drafts, long-form writing, source synthesis, and argument development. Emphasize source traceability, audience, thesis, outline, citation expectations, assumptions, methodology, and separation of evidence from interpretation.
- Second-brain or ideation: use for personal knowledge bases, diary-like workspaces, idea development, and exploratory notes. Emphasize low-friction capture, privacy, durable naming, linking conventions, uncertainty, and sync/backup awareness.
- Automation or scripting: use for local utilities, initialization scripts, data movement, and repeatable operational tasks. Emphasize idempotency, dry-run behavior where useful, explicit paths, logging, safe failure modes, and protection against destructive commands.
- Sensitive or private project: add as a secondary profile when the target may contain personal data, user data, credentials, payments, proprietary material, client data, health data, financial data, or other sensitive information. Emphasize minimization, redaction, secrets handling, and explicit export/sync/publication risks.

Minimum generated `style.md` structure:

```markdown
# Project Style Guide

## Style Basis

- Project type:
- Primary style profile:
- Secondary style profile:
- Intended use:
- Primary audience:
- Risk level:
- Why these conventions apply:

## Global Conventions

## Project-Specific Conventions

## Security And Privacy Conventions

## File-Specific Guidance

### `index.md`

### `context.md`

### `style.md`

### `sessions/YYYY-MM-DD.md`
```

Profile-specific guidance:

- Data science or ML: reproducibility, data leakage prevention, train/validation/test boundaries, experiment tracking, notebook execution order, artifact versioning, metric discipline.
- Production app, API, website, or SaaS: secure defaults, input validation, authentication/authorization expectations, secrets handling, dependency hygiene, logging without sensitive data, tests, deployment checks, rollback-aware changes.
- Library or package: API stability, semantic versioning, typing, tests, public documentation, compatibility policy, changelog expectations.
- Writing, diary, notes, or second brain: clarity, linking conventions, metadata/tagging, privacy expectations, durable naming, low-friction capture, sync/backup awareness.
- Automation or scripting: idempotency, dry-run behaviour where useful, explicit paths, logging, safe failure modes, protection against destructive commands.
- Research project: source traceability, assumptions, methodology notes, reproducibility, separation of evidence from interpretation.

Security must be proportional:

- Production-facing, public, networked, or user-data projects require explicit security best practices.
- Private local knowledge projects require privacy and backup guidance, not unnecessary production process.
- If uncertain, protect secrets, credentials, personal data, and destructive operations by default.

## Step 8: Create First Session Log

Create `.AGENTS/sessions/YYYY-MM-DD.md` and record:

- bootstrap date
- project classification
- questions asked and answers received
- files created
- assumptions
- follow-up gaps

Keep sessions append-only.

## Step 9: Validate Bootstrap

Bootstrap is incomplete until all checks pass:

- `AGENTS.md` exists.
- `CLAUDE.md` exists and routes Claude Code to `AGENTS.md`.
- `GEMINI.md` exists and routes Gemini CLI to `AGENTS.md`.
- `.AGENTS/agent-rules.md` exists and defines operating-mode memory rules.
- `.AGENTS/project-bootstrap.md` exists and is marked bootstrap-only.
- `.AGENTS/index.md` exists, is concise, and points only to active files.
- `.AGENTS/context.md` exists and includes project type, risk, purpose, current state, traversal guidance, and memory rules.
- `.AGENTS/style.md` exists and matches the project type, intended use, and risk level.
- `.AGENTS/sessions/YYYY-MM-DD.md` exists and records bootstrap decisions.
- No required bootstrap output is missing.
- No stale file references point agents to obsolete memory files.
- Security posture matches risk level.
- `context.md` is enough for repo traversal without guessing.
- No active operating-mode file requires agents to read bootstrap guidance after initialization.

After validation, switch to operating mode and stop using this file.
