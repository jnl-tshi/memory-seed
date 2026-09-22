---
memory-system-version: 2.21
governing_adr: adr_session_decision_authority
tags:
  - memory-seed
  - skill
  - end-of-turn
---

# End Of Turn Skill

Use this skill when running the Memory Seed end-of-turn routine, `/esr`, or any closeout that should leave durable memory current.

## Procedure

0. Run `memory-seed esr` (add `--date YYYY-MM-DD` for a session crossing midnight): one read-only
   report covering integrity, topics, lifecycle link gaps, ADR inverse-coverage candidates with
   attached recommendations, registered worktree posture, unregistered physical worktree residue,
   seed-twin drift. If an ADR section contains work, load `adr_sweep.md` for adjudication and
   orchestration; ESR discovers and recommends but never writes an ADR change.
   Read every section - each prints even when clean, so a skipped check is visible. Use its
   sections for steps 5, 12, and 13 instead of re-running the underlying commands one by one.
1. Resolve the active session target with `memory-seed session target` when the target is uncertain.
2. Run the Record Harvest from `.memory-seed/skills/session_logging.md` before composing the entry:
   identify every durable accepted choice, then choose single-decision, multi-decision, or separate
   entries from that list. The harvest includes the lifecycle questions: does any harvested decision
   replace/remove (`replaces`) or extend-while-still-valid (`evolves`) an earlier entry, and did
   the turn rename, relocate, or remove any artifact (record a `continuity:` block with old and new
   names). It also asks whether the turn established durable project facts that are
   not decisions (roles, codenames, cadences, budgets) - those are promoted to
   `.memory-seed/index.md` under `## Active State` in the same turn, because an entry body
   has no home for a fact with no `R:`.
3. Append the session entry to the active session target before doing other closeout work. Use
   `.memory-seed/skills/session_logging.md` for the exact entry schema, DRAFTS labels,
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
9. **Roadmap reconciliation (human question, never automated):** did this turn implement, resolve,
   or unblock anything a roadmap/plan document still presents as pending — `docs/2_Todo/0_NEXT_STEPS.md`,
   the item's own plan/proposal doc, or a lane README? If yes, update those lines **in the same
   workstream** (and move the doc to its outcome lane when its work is done), or record in the session
   entry why the prose is deliberately left unchanged. Structural checks cannot catch this: `docs check`
   validates links and YAML, not whether narrative delivery state matches reality — a shipped item that
   the roadmap still calls pending misleads the next session's orientation read. Never edit roadmap
   prose by automation; this is a judgement question asked of a human (or answered in the entry).
10. If work occurred in a sub-project runtime, review whether the parent or root runtime needs a brief coordination summary.
11. Run the smallest verification that proves the work, broadening when the changed behavior is
    shared. A completion claim needs fresh evidence from after the relevant change: record the
    command or check, changed scope, execution point or freshness marker, and outcome. Classify it
    as `passed`, `failed`, `blocked`, `unavailable`, or `waived`; only `passed` supports a passing
    completion claim. For a non-run check, record the omission reason; a `waived` check also names
    the granting authority and is never a pass. Pre-change evidence is stale. This does not weaken
    any stricter project policy requiring tests before behavior changes.
12. Run the orphan & artifact sweep for files, features, commands, generated artifacts, and scratch output touched by this session.
13. Run the Stale Worktree Sweep when the project uses git worktrees.
14. Run the Persona evolution check when a persona is active.
15. Run the Skill evolution check when a persona is active.
16. Check for unregistered persona files and escalate to persona onboarding when files exist without registry entries.
17. Run the Baseline-promotion check for general rules, skills, or runbooks worth promoting beyond this project.

## Consolidation Review

Load `.memory-seed/skills/memory_consolidation.md` when recent work created durable facts that should move from session history into `index.md`, `policy.md`, or a skill. Promote stable conclusions and current operating facts, not full decision history.

Review consolidation when:

- more than three meaningful entries accumulated since last consolidation
- project direction, architecture, release process, CLI behavior, workflow rules, file ownership, or durable risk changed
- session notes became long enough that future agents will struggle to scan them
- a release, publish, migration, bootstrap repair, security decision, or major refactor completed
- `index.md`, `policy.md`, or a skill no longer reflects current state

## Lifecycle Link Sweep

Write-time YAML (the Record Harvest's lifecycle questions in step 2) is the first line of defense;
this sweep is the safety net for edges you could not know at authoring time. It exists because typed
lifecycle edges rot silently otherwise: genuine supersessions get logged as generic
`related_entries` and the distinction collapses.

- After reviewing the "Lifecycle link gaps" section of the `memory-seed esr` report (step 0), run
  `memory-seed link audit --date <today> --apply` with today's concrete date. It compares this
  session's entries (targets) against the full corpus (candidates) and creates chronologically ordered,
  machine-detectable `classify_pending: true` sidecar stubs. The candidate ids remain comments: the
  command never auto-classifies a relationship and never writes a live edge.
- A human must classify each stub with the litmus: the new entry *retires* the candidate ->
  `replaces`; *refines it while it stays valid* -> `evolves`; genuinely just connected ->
  `related_entries`. Not every candidate deserves an edge - shared files can be coincidental, so delete
  or leave unresolved stubs rather than inventing a relationship.
- After human approval, replace the accepted stubs with live edges in the day's link sidecar
  `.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md` - never by reopening a written entry
  (append-only). Each block is keyed to the SOURCE (newer) entry:
  `## <entry's timestamp> - <short label>` + a fenced yaml with `entry_id:` and the
  `replaces:`/`evolves:`/`related_entries:` lists pointing at older targets.
- Stub creation itself is mechanical and safe; ask the user for approval before converting any stub
  into a live edge (same gate as persona evolution), showing the evidence and proposed classification.
- Finish with `memory-seed links check` - live sidecar edges join the dangling and forward-only guards,
  while unresolved stubs remain warning-only and inert.

Skip silently when the audit reports no gaps.

## Orphan And Artifact Sweep

Scope the sweep to this session's changes.

- Additions: confirm every new file, function, module, skill, persona, route, command, config key, or generated artifact is referenced, registered, linked, exported, routed, or intentionally standalone.
- Deletions and renames: search for old names and paths; resolve or flag dangling references.
- Scratch and debris: flag temporary files, commented-out code, debug output, half-removed features, stray untracked directories, backups, and generated output that should not persist.
- Dead-code tools: run an already-declared tool only when the project provides one. Do not install a tool solely for ESR.

Do not delete user-owned or pre-existing files on the sweep alone. Flag and ask when ownership is unclear.

## Stale Worktree Sweep

Applies to every registered worktree and every physical candidate under `.claude/worktrees/`,
`.codex/worktrees/`, `.gemini/worktrees/`, `.cursor/worktrees/`, or a configured equivalent - not
just candidates created during this session.

- Start from the Worktrees section of `memory-seed esr`; it discovers candidates but never authorizes
  cleanup.
- Load `worktree_reconciliation.md` before assessing, recommending, recovering, discarding, or removing
  any dirty, stale, detached, or deregistered candidate. Follow its session-first storyline, Git-second
  verification, six-way content classification, one-summary-per-worktree, exact-target approval, branch
  preservation, and post-removal verification contract.
- Do not turn a clean/merged classifier result into a deletion recommendation without that review, and
  do not treat approval for one candidate as approval for another.
- Immediate cleanup of the exact clean source worktree after a successful guarded integration remains
  governed by `agent_collaboration.md`; the broader stale-worktree sweep uses the reconciliation skill.

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
