---
memory-system-version: 2.14
tags:
  - memory-seed
  - skill
  - end-of-turn
---

# End Of Turn Skill

Use this skill when running the Memory Seed end-of-turn routine, `/esr`, or any closeout that should leave durable memory current.

## Procedure

1. Append a session entry to the active session target before doing other closeout work. Use `memory-seed session target` when the target is uncertain.
2. Use `.memory-seed/skills/session_logging.md` for the exact entry schema, DRAFT labels, `related_entries`, timestamp, and append-only rules.
3. Review whether `.memory-seed/index.md` needs updated topology, active state, inheritance, current risk, or skill pointers.
4. Review whether `.memory-seed/policy.md` needs durable behavioral-policy changes.
5. Review whether any `.memory-seed/skills/*.md` runbook changed.
6. If work occurred in a sub-project runtime, review whether the parent or root runtime needs a brief coordination summary.
7. Run the smallest verification that proves the work.
8. Run the orphan & artifact sweep for files, features, commands, generated artifacts, and scratch output touched by this session.
9. Run the Persona evolution check when a persona is active.
10. Run the Skill evolution check when a persona is active.
11. Check for unregistered persona files and escalate to persona onboarding when files exist without registry entries.
12. Run the Baseline-promotion check for general rules, skills, or runbooks worth promoting beyond this project.

## Consolidation Review

Load `.memory-seed/skills/memory_consolidation.md` when recent work created durable facts that should move from session history into `index.md`, `policy.md`, or a skill. Promote stable conclusions and current operating facts, not full decision history.

Review consolidation when:

- more than three meaningful entries accumulated since last consolidation
- project direction, architecture, release process, CLI behavior, workflow rules, file ownership, or durable risk changed
- session notes became long enough that future agents will struggle to scan them
- a release, publish, migration, bootstrap repair, security decision, or major refactor completed
- `index.md`, `policy.md`, or a skill no longer reflects current state

## Orphan And Artifact Sweep

Scope the sweep to this session's changes.

- Additions: confirm every new file, function, module, skill, persona, route, command, config key, or generated artifact is referenced, registered, linked, exported, routed, or intentionally standalone.
- Deletions and renames: search for old names and paths; resolve or flag dangling references.
- Scratch and debris: flag temporary files, commented-out code, debug output, half-removed features, stray untracked directories, backups, and generated output that should not persist.
- Dead-code tools: run an already-declared tool only when the project provides one. Do not install a tool solely for ESR.

Do not delete user-owned or pre-existing files on the sweep alone. Flag and ask when ownership is unclear.

## Persona Evolution Check

When a persona is active, identify up to three evidence-backed behavior changes that would improve that persona.

- Draft proposed changes to `.agents/<slug>.md`.
- Explain what should be added, changed, or removed and why.
- Ask the user for approval before editing the persona file.
- On approval, append a dated entry to the persona file's `## Project Adaptations` section and record approval in the session log.

Skip silently when no lesson emerged.

## Skill Evolution Check

When a persona is active and a repeated workflow pattern is not covered by an existing skill:

- Propose a role-specific skill file name and trigger.
- Draft the skill structure: YAML frontmatter, title, procedure, output expectations.
- Ask the user for approval before writing.
- On approval, add the skill file, register it in `skills/index.md` with `persona: <slug>`, update the persona's role-specific skills section, and log the change.

Skip silently when no reusable skill gap emerged.

## Baseline-Promotion Check

If an approved adaptation is general enough for reuse beyond this project, record a candidate in `.memory-seed/plans/` for later human action. This check may create `.memory-seed/plans/` when needed, but it never edits shared templates or upstream repositories automatically.

