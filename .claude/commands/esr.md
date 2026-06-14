Run the end-of-session routine defined in `.memory-seed/agent-rules.md` (End Of Turn section). Execute all steps in order:

1. Append a session log entry to `.memory-seed/sessions/YYYY-MM-DD.md` (today's date from system clock). Use the multi-decision DRAFT shape if the session produced multiple decisions; otherwise the meaningful decision shape. Include `agent_name` for any active persona.

2. Review `.memory-seed/index.md` — update Active State, Topology, or Design Decisions if anything durable changed this session.

3. Review `.memory-seed/policy.md` — update only if a behavioral constraint changed.

4. Orphan & artifact sweep, scoped to this session's changes (`git diff`/`git status`): confirm every file/function/skill/persona/route/config-key you *added* is referenced somewhere (else wire it in or remove it); grep for dangling references to anything you *deleted or renamed*; flag scratch/debris (temp files, commented-out code, debug output, half-removed features, stray untracked dirs, `*.bak`). Optionally run a declared dead-code tool (vulture/ruff, knip, ArchUnit, cppcheck) if the project already has one — do not install one. Record unresolved items as Follow-ups; do not delete pre-existing or user-owned files on this sweep alone — flag and confirm.

5. Persona evolution check: for each active persona in `.agents/_registry.yaml`, identify up to 3 patterns from this session that should change how the persona behaves. Draft proposed changes and present them to the user for approval before editing any file. Log approved changes in `## Project Adaptations` and in the session entry.

6. Skill evolution check: if a repeating workflow gap emerged that no existing `.memory-seed/skills/` file covers, draft a new skill file and present it for approval before writing.

7. Check for any `.agents/*.md` files not listed in `.agents/_registry.yaml`. If found, run the persona onboarding flow from `project-bootstrap.md` Step 9e.

Do not skip steps. Do not defer the session log write.
