# .agents/ — Agent Persona Library

This folder ships with every `memory-seed init` and provides vendor-neutral persona templates that any LLM can inhabit. Each persona defines an identity, operating rules, memory protocol, and session discipline for a specific role.

---

## Available Personas

| File | Agent Name | Role |
|------|-----------|------|
| `developer.md` | `developer` | Software Engineer / Staff IC |
| `content-creator.md` | `content-creator` | Content Strategist / Writer |
| `researcher.md` | `researcher` | Research Engine / Knowledge Architect |
| `sales-rep.md` | `sales-rep` | Sales Operator / Pipeline Manager |
| `solo-founder.md` | `solo-founder` | Co-founder / Generalist |

---

## Activation and Deactivation

Personas are controlled by `.agents/_registry.yaml`. Set `status: active` to enable a persona; `status: inactive` to disable it.

Bootstrap generates `_registry.yaml` when you first run `memory-seed init` in a project. Edit it at any time to switch personas.

**Example registry:**
```yaml
agents:
  developer:
    file: developer.md
    role: Software Engineer / Staff IC
    status: active
  solo-founder:
    file: solo-founder.md
    role: Co-founder / Generalist
    status: inactive
```

When an agent starts a session, it reads `_registry.yaml`, loads all `status: active` persona files, and applies those rules alongside `agent-rules.md` and `policy.md`.

**Multiple active personas:** Allowed. The persona most relevant to the current task governs. When ambiguous, the first active entry in `_registry.yaml` is the default.

---

## Adding a New Persona

**Quick path (existing persona as starting point):**

1. Copy any existing persona file: `cp developer.md data-scientist.md`
2. Save it to `.agents/data-scientist.md`
3. At the next session start, the agent detects the unregistered file and runs the onboarding flow automatically:
   - Adds or corrects YAML frontmatter (`agent_name`, `memory_protocol`, `vendor_neutral`, `tags`)
   - Rewrites the Memory Protocol section to use `.memory-seed/` paths (if it references a separate `memory/` folder)
   - Adds `## Project Adaptations` and `## Skills` sections if missing
   - Runs personalization: asks for entity name (or generates one), confirms user name, asks for business name
   - Routes relevant skills from `.memory-seed/skills/` and offers to generate missing ones
   - Adds the persona to `_registry.yaml` with `status: active`

**Starting from scratch:**

Write a plain Markdown file describing the role. The onboarding flow will handle all formatting. The minimum content needed:
```markdown
# [Role] Operating System

## I. Identity

You are [describe the role and its purpose].

## III. Operating Rules

[Domain-specific rules and standards for this role]
```

The agent fills in the Memory Protocol, Skills, Project Adaptations, and Persona Evolution sections during onboarding.

The `.agents/` folder is project-local: `memory-seed update` never overwrites it once created, so custom personas and their evolved content survive upgrades.

---

## Persona Evolution (Lessons Learned)

Personas grow smarter as the project progresses. At session end, the active agent may propose changes to the persona file based on patterns observed during the session. The flow:

1. Agent drafts proposed change(s): what to add/change/remove and why (evidence from this session).
2. Agent presents proposals to the user for approval. **No edits happen until the user approves.**
3. On approval, the agent:
   - Applies the edit to the relevant section of the persona file.
   - Appends an entry to the `## Project Adaptations` section at the bottom of the persona file.
   - Appends a session log entry (`agent_name: <slug>`, D/R/F + "Signed: user approved YYYY-MM-DD HH:MM").

**Project Adaptations entry format:**
```markdown
### YYYY-MM-DD — Short description of what changed
Session: ms-<entry_id> | Approved by: <user_initials>
Section changed: [section name]
Rationale: [one-line reason from session]
```

This creates three layers of traceability: the session log decision record, the in-file changelog, and the git diff.

If no lessons emerged, skip the proposal — no empty prompts.

---

## Memory Protocol

Each persona's Memory Protocol section points to the memory-seed runtime:
- `.memory-seed/index.md` — active state and current focus
- `.memory-seed/sessions/` (last 2 files) — recent decisions and open threads
- `.memory-seed/policy.md` — behavioral constraints and preferences
- `memory_search` MCP — historical context beyond the last 2 sessions

Persona session entries use `agent_name: <slug>` in the entry YAML block (see `agent-rules.md` for the full format). This lets `memory_search` filter entries by persona.

---

## Vendor Neutrality

Persona files use `.memory-seed/` paths and plain Markdown conventions — no LLM-specific APIs, directives, or syntax. Any file-reading AI coding agent (Claude, Gemini, Codex, GPT-4, or a future model) can read and apply these files.
