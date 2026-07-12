---
memory-system-version: 2.17
tags:
  - memory-seed
  - skill
  - end-of-turn
---

# End Of Turn Skill

Use this skill when running the Memory Seed end-of-turn routine, `/esr`, or any closeout that should leave durable memory current.

## Procedure

0. Run `memory-seed esr` (add `--date YYYY-MM-DD` for a session crossing midnight): one read-only
   report covering integrity, topics, lifecycle link gaps, worktree posture, and seed-twin drift.
   Read every section - each prints even when clean, so a skipped check is visible. Use its
   sections for steps 5, 11, and 12 instead of re-running the underlying commands one by one.
1. Resolve the active session target with `memory-seed session target` when the target is uncertain.
2. Run the Decision Harvest from `.memory-seed/skills/session_logging.md` before composing the entry:
   identify every durable accepted choice, then choose single-decision, multi-decision, or separate
   entries from that list. The harvest includes the lifecycle questions: does any harvested decision
   replace/remove (`supersedes`) or extend-while-still-valid (`evolves`) an earlier entry, and did
   the turn rename, relocate, or remove any artifact (record a `continuity:` block with old and new
   names).
3. Append the session entry to the active session target before doing other closeout work. Use
   `.memory-seed/skills/session_logging.md` for the exact entry schema, DRAFT labels,
   `related_entries`, timestamp, and append-only rules.
4. If the entry has a decision-diagram positive trigger from `session_logging.md` (branch or merge
   topology, migration, schema/layout compatibility flow, multi-agent concurrency, command lifecycle,
   or retrieval/data pipeline), create a Mermaid sidecar in
   `.memory-seed/sessions/diagrams/YYYY-MM/YYYY-MM-DD.md` in the same turn unless the diagram would
   add no structure beyond prose. If a positive trigger is present and no sidecar is written, record
   the reason in the session entry.
5. Run the Lifecycle Link Sweep once the session's entries are appended.
6. Review whether `.memory-seed/index.md` needs updated topology, active state, inheritance, current risk, or skill pointers.
7. Review whether `.memory-seed/policy.md` needs durable behavioral-policy changes.
8. Review whether any `.memory-seed/skills/*.md` runbook changed.
9. If work occurred in a sub-project runtime, review whether the parent or root runtime needs a brief coordination summary.
10. Run the smallest verification that proves the work.
11. Run the orphan & artifact sweep for files, features, commands, generated artifacts, and scratch output touched by this session.
12. Run the Stale Worktree Sweep when the project uses git worktrees.
13. Run the Persona evolution check when a persona is active.
14. Run the Skill evolution check when a persona is active.
15. Check for unregistered persona files and escalate to persona onboarding when files exist without registry entries.
16. Run the Baseline-promotion check for general rules, skills, or runbooks worth promoting beyond this project.

## Consolidation Review

Load `.memory-seed/skills/memory_consolidation.md` when recent work created durable facts that should move from session history into `index.md`, `policy.md`, or a skill. Promote stable conclusions and current operating facts, not full decision history.

Review consolidation when:

- more than three meaningful entries accumulated since last consolidation
- project direction, architecture, release process, CLI behavior, workflow rules, file ownership, or durable risk changed
- session notes became long enough that future agents will struggle to scan them
- a release, publish, migration, bootstrap repair, security decision, or major refactor completed
- `index.md`, `policy.md`, or a skill no longer reflects current state

## Lifecycle Link Sweep

Write-time YAML (the Decision Harvest's lifecycle questions in step 2) is the first line of defense;
this sweep is the safety net for edges you could not know at authoring time. It exists because typed
lifecycle edges rot silently otherwise: genuine supersessions get logged as generic
`related_entries` and the distinction collapses.

- Start from the "Lifecycle link gaps" section of the `memory-seed esr` report (step 0) - it is
  `link audit --date <today>`: this session's entries (targets) against the full corpus
  (candidates), flagging pairs that share `F:` files or topics with no recorded edge. File overlap
  surfaces a candidate even when a `related_entries` link already exists (the upgrade case);
  topic-only overlap is suppressed by any existing edge. Run `memory-seed link audit` directly only
  when you need a different scope or more candidates per entry.
- Classify each flagged candidate with the litmus: the new entry *retires* it -> `supersedes`;
  *refines it while it stays valid* -> `evolves`; genuinely just connected -> `related_entries`.
  Not every flag deserves an edge - shared files can be coincidental; skip those.
- Record the accepted edges in the day's link sidecar
  `.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md` - never by reopening a written entry
  (append-only). Each block is keyed to the SOURCE (newer) entry:
  `## <entry's timestamp> - <short label>` + a fenced yaml with `entry_id:` and the
  `supersedes:`/`evolves:`/`related_entries:` lists pointing at older targets.
- Ask the user for approval before writing the sidecar (same gate as persona evolution): show the
  proposed edges with their evidence and classification.
- Finish with `memory-seed links check` - sidecar edges join the dangling and forward-only guards.

Skip silently when the audit reports no gaps.

## Orphan And Artifact Sweep

Scope the sweep to this session's changes.

- Additions: confirm every new file, function, module, skill, persona, route, command, config key, or generated artifact is referenced, registered, linked, exported, routed, or intentionally standalone.
- Deletions and renames: search for old names and paths; resolve or flag dangling references.
- Scratch and debris: flag temporary files, commented-out code, debug output, half-removed features, stray untracked directories, backups, and generated output that should not persist.
- Dead-code tools: run an already-declared tool only when the project provides one. Do not install a tool solely for ESR.

Do not delete user-owned or pre-existing files on the sweep alone. Flag and ask when ownership is unclear.

## Stale Worktree Sweep

Applies to every worktree under `.claude/worktrees/` and `.codex/worktrees/` (or equivalent), not
just ones this session created - other agents (Claude, Codex, or otherwise) may leave theirs behind
too.

- Start from the "Worktrees" section of the `memory-seed esr` report (step 0): it already lists
  every worktree with its branch, commits ahead of the integration branch, and dirty-file count,
  and marks merged-and-clean ones as STALE CANDIDATE. Fall back to `git worktree list` +
  `git log <integration>..<branch>` + `git status --short` per worktree only when the report is
  unavailable.
- A merged branch can still carry working-tree state its own history never saw - the dirty count
  covers this, but re-check `git status --short` inside the worktree immediately before removal.
- If uncommitted changes exist, diagnose before touching them:
  - Genuinely stale/superseded (already reflected in the integration branch some other way, or pure
    formatting/line-ending noise) - safe to discard, but still name the specific worktree and diff
    and get explicit user confirmation before discarding; a prior general "clean them up" does not
    by itself authorize discarding a diff turning out to hold real content.
  - Unique, never-recorded content (e.g. a session-log entry that exists nowhere else) - recover it
    into the canonical target first (commit it properly), then remove the worktree.
- Only remove a worktree once its branch is confirmed merged (or the user explicitly says to
  abandon it) and any uncommitted content has been resolved - recovered or discarded with consent.
- Prefer the platform's worktree-removal tool when the worktree was entered via `EnterWorktree`;
  otherwise `git worktree remove` (add `--force` only after the above checks pass), then
  `git worktree prune` to clear stale metadata.

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
