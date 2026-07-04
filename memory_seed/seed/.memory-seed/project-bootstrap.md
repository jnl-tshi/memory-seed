---
memory-system-version: 2.15
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
.agents/
  README.md
  developer.md
  content-creator.md
  researcher.md
  sales-rep.md
  solo-founder.md
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

## Step 9: Activate Agent Personas

If `.agents/` does not exist, skip this step.

### 9a. Select personas

List the available persona files from `.agents/`. Ask the user: which persona(s) should be active for this project? Multiple is allowed. None is allowed.

### 9b. Personalize each activated persona

For each activated persona, run the following sub-steps in order. Skip sub-steps where the value is already resolved (i.e., `_registry.yaml` already exists and the persona entry has `entity_name` set).

**Entity name (the persona's identity)**

Ask: "What should I be called as your [role]? Press Enter to let me pick."

If the user provides a name, use it. If skipped, generate a fun single-word name with a pop-culture reference that fits the project domain and the persona's role archetype:

- Dev tool / OSS â†’ hacker/technologist fiction: Neo, Ada, Linus, Turing, Grace
- Startup / product â†’ builder mythology: Stark, Woz, Palmer, Musk (toned), Rhodes
- Content / media â†’ writer canon: Gonzo, Ogilvy, Didion, Bernbach
- Research / academic â†’ scientist fiction: Asimov, Sagan, Feynman, Curie
- Sales / growth â†’ fictional closers: Ari, Harvey, Boiler (toned)

State the name and the reference so the user can veto: "I'll go by *Stark* â€” Iron Man's relentless builder energy felt right for a solo dev startup. Want a different one?"

Rules: one word, no title prefix, loosely tied to the role and project vibe.

**User's name**

Try to infer from `git config user.name`. Present as: "I'll address you as [inferred name]. Is that right?" If inference failed, ask: "What should I call you?"

**Business or project name**

Try to infer from `pyproject.toml [project] name`, `package.json name`, the README `# Title`, or the project folder name. Present as: "I'll refer to the project as [inferred name]. Correct?" If inference failed, ask: "What's the business or project name?"

**Substitute placeholders in the persona file**

After confirming all three values, edit `.agents/<file>.md` in-place, replacing:
- `[YOUR_ENTITY_NAME]` â†’ resolved entity name
- `[YOUR_NAME]` â†’ resolved user name
- `[YOUR_BUSINESS_NAME]` â†’ resolved business name
- `[YOUR_BRAND_NAME]` (content-creator only) â†’ resolved business name, or ask separately if brand differs from product

### 9c. Route skills for each activated persona

For each activated persona, identify which skills from `.memory-seed/skills/` are relevant to its role and populate the `### Mapped Skills` table in the persona file.

Default mappings:

| Persona | Skills to map |
|---|---|
| `developer` | code_search, local_compilation, data_architecture, security_triage |
| `solo-founder` | code_search, local_compilation, release_publishing, security_triage |
| `content-creator` | code_search |
| `researcher` | code_search, data_architecture |
| `sales-rep` | *(no default mapping â€” likely needs role-specific skills; see gap detection below)* |

For custom personas, map skills based on the persona's role description and operating rules.

**Gap detection and skill generation**

After mapping existing skills, ask: "Does [entity_name] need any workflows that aren't covered by the existing skills?" If yes, for each identified gap:

1. Draft a new skill file in the standard memory-seed format:
   ```markdown
   ---
   tags:
     - memory-seed
     - skill
     - [persona-slug]
     - [skill-name]
   ---

   # [Skill Name]

   [One-sentence description of when and why to use this skill.]

   ## Procedure

   1. [Step]
   2. [Step]

   ## Output

   - [What to produce or record]
   ```
2. Show the draft to the user for approval. Do not write until approved.
3. On approval:
   - Write to `.memory-seed/skills/<persona-slug>-<skill-name>.md`
   - Add a trigger entry to the `skills:` list in `.memory-seed/skills/index.md`:
     ```yaml
     - skill: <persona-slug>-<skill-name>.md
       required: false
       persona: <persona-slug>
       load_when:
         - [trigger conditions]
       do_not_load_when:
         - [exclusion conditions]
     ```
   - Add the filename to the `### Role-Specific Skills` section of the persona file

The `persona:` field in `skills/index.md` entries signals that the skill only loads when that persona is active.

### 9d. Write `_registry.yaml`

Write `.agents/_registry.yaml` with the selections and resolved values. Set unselected personas to `inactive`.

```yaml
# .agents/_registry.yaml
# Generated by bootstrap. Edit to activate/deactivate personas.
# Add new entries here to register custom personas created in this folder.

agents:
  solo-founder:
    file: solo-founder.md
    role: Co-founder / Generalist
    status: active
    entity_name: Stark
    user_name: Jean Nathan
    business_name: Foundry
  developer:
    file: developer.md
    role: Software Engineer / Staff IC
    status: active
    entity_name: Ada
    user_name: Jean Nathan
    business_name: Foundry
  content-creator:
    file: content-creator.md
    role: Content Strategist / Writer
    status: inactive
    entity_name: null
    user_name: null
    business_name: null
```

`entity_name`, `user_name`, and `business_name` in the registry are informational. The persona file is authoritative â€” placeholders are already replaced there.

`_registry.yaml` is not a seed file â€” it is never overwritten by `memory-seed update`. Custom personas and activation choices survive upgrades.

### 9e. Onboard unregistered persona files

After writing `_registry.yaml`, check for `.agents/*.md` files that are not listed in the registry (custom personas the user dropped in). For each unregistered file:

1. Read the file. Check for required YAML frontmatter (`agent_name`, `memory_protocol`, `vendor_neutral`, `tags`). If missing, add it, deriving `agent_name` from the filename slug.
2. Check if the Memory Protocol section points to `.memory-seed/` paths. If it references a separate `memory/` folder, rewrite it to the standard memory-seed format.
3. Check for `## Project Adaptations` section at the bottom. If missing, append it.
4. Check for `## Skills` section. If missing, add it with `### Mapped Skills` and `### Role-Specific Skills` subsections.
5. Run personalization (sub-steps 9b).
6. Run skill routing (sub-step 9c).
7. Add to `_registry.yaml` with `status: active`.

The user only sees the questions; the formatting steps happen silently.

## Step 10: Create First Session Log

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
entry_id: mse_0123456789abcdef
user_initials: USER
agent_type: codex
project_path: .
subproject_path: null
```
````

Generate `entry_id` as a deterministic 80-bit `mse_` ID from metadata only: timestamp, title, user initials, agent type, project path, and subproject path. Do not hash the entry body. Legacy `ms-` IDs remain valid and must not be rewritten.

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

## Step 11: Validate Bootstrap

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
