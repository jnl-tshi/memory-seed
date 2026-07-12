---
memory-system-version: 2.18
tags:
  - memory-seed
  - skill
  - skill-architecture
---

# Skill Architecture

Use this skill when changing Memory Seed skills, profiles, trigger registry entries, or the boundary between always-on control-plane rules and lazy-loaded runbooks.

## Startup Contract Boundary

`agent-rules.md` is the non-deferrable startup contract. It should keep only:

- runtime discovery and operating read order
- authority and inheritance rules
- compact file ownership and change-permission gates
- skill-loading procedure and high-signal trigger pointers
- the end-of-turn obligation

Keep procedural details in skills. A rule can move out of `agent-rules.md` only when the remaining text lets an agent safely know which skill to load before acting.

## Existing Skill Homes

Prefer extending an existing skill over creating a new one:

| Guidance type | Skill home |
| --- | --- |
| Session schema, DRAFT fields, append-only repair | `session_logging.md` |
| Closeout, ESR, orphan sweep, consolidation review | `end_of_turn.md` |
| Recency/topical retrieval and current-file authority | `history_retrieval.md` |
| Public-memory, redaction, reusable-template hygiene | `memory_hygiene.md` |
| Risk tiers, STOP categories, control-plane escalation | `risk_signaling.md` |
| Subagents, branches, worktrees, merge handoffs | `agent_collaboration.md` |
| Runtime health, orphan skills, seed/live sync | `memory_doctor.md` |
| Proposal inbox/todo/completed/reference flow | `proposal_lifecycle.md` |

Create a new skill only when the procedure is reusable, cross-project, and does not fit an existing owner.

## Trigger Registry Discipline

`skills/index.md` is a dispatch table, not a manual.

- Keep each entry to a few concrete `load_when` bullets.
- Put examples, edge cases, and rationale inside the skill file.
- Use specific verbs: adding, removing, renaming, splitting, registering, moving, deciding.
- Include `do_not_load_when` only when it prevents likely over-loading.
- Register only installed skills in generated project registries.

## Core, Optional, And Profiles

- Core skills are installed in every project because they protect runtime safety or universal memory hygiene.
- Optional skills belong to profiles when they serve a project type, role, or workflow.
- Do not promote a skill to core just because Memory Seed itself needs it.
- Update `SKILL_PROFILES`, `OPTIONAL_SKILL_NAMES`, descriptions, seed inventory, tests, and docs together.

## Seed / Live Parity

When a reusable skill changes in this repository:

1. Update the live `.memory-seed/skills/<name>.md`.
2. Update the seed twin under `memory_seed/seed/.memory-seed/skills/<name>.md`.
3. Update live and seed `skills/index.md` when trigger behavior changes.
4. Update `.memory-seed/index.md` when this dogfood runtime should advertise the skill.
5. Run parity, registry, doctor, links, encoding, and unit-test checks appropriate to the change.

Do not write project-specific paths, identities, or decisions into seed skills.
