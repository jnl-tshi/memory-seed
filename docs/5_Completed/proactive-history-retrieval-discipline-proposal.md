---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - control-plane
  - agent-rules
  - retrieval
---

# Proactive "consult memory for the why" discipline (portable, all-agent)

Status: **SHIPPED** 2026-07-13 — the proactive retrieve-the-why rule is seeded in `agent-rules.md` Working
Principles, `history_retrieval.md`, and the developer persona, all with seed twins (merged to main).
Belongs in `docs/5_Completed/`; physical relocation batched into lifecycle Phase 2.
Priority: P2 — control-plane behavior change; low blast radius (doc/skill edits + seed twins), high
leverage (every agent, every project inherits it).
Source: User 2026-07-13 — observed that agents (Claude included) read source files for the *current
condition* of code but rarely consult session memory for the *reasoning*, and that a personal
Claude-Code memory note (`~/.claude/.../feedback_consult_memory_for_why.md`) fixes it only for Claude,
not for Codex/Gemini/Cursor/Copilot and does not ship with the seed. Requested the behavior be
developed into `agent-rules` and/or the personas so all agents benefit.

## The gap (not what it first looks like)
The behavior is **already partly in the control plane** - so this is a sharpening, not an addition:

- [`agent-rules.md`](../../.memory-seed/agent-rules.md) "History Retrieval And Conflict Resolution"
  already says to use retrieval when *"why was this done"* matters, and "Recency vs. Topical
  Retrieval" already draws the distinction: **current files are the active authority; session history
  is evidence and reason, not automatic authority.**
- `history_retrieval.md` already carries the mechanics (`memory_search`/`memory_get_chunk`,
  topical-vs-recency, conflict handling).

Two real gaps remain:
1. **The rule is passive/reactive** ("when 'why was this done' matters"), not a **proactive trigger**
   fired *before* a design or change decision. Agents (including this session's) under-heed a passive
   rule and re-derive settled decisions or trip documented landmines.
2. **The only place the sharpened habit currently lives is Claude-Code-personal memory**, which no
   other agent reads and which does not ship in the seed. It must move into the vendor-neutral,
   seeded control plane.

Concrete misses this session that a proactive rule would have caught: the append-only fuse guard that
*blocked* a merge (documented in the `session merge-branch` decision) was hit as a surprise; the
`pr`-mode branch-prep design was re-derived though the fuse rationale was already logged.

## Design decision that constrains the home
`memory_search` surfaced `mse_hejpp9whj0nn8jyy` (2026-07-03), "**Working Principles over a new lazy
skill**": cross-cutting, always-on principles belong in `agent-rules.md`'s **Working Principles**
section, not a new skill (skills are lazy-loaded and would be missed at the decision point). And the
2026-07-01 lazy-skill extraction keeps `agent-rules.md` deliberately slim. So: sharpen an *existing*
line, do not add a skill, and respect the line budget.

## Proposal (layered, vendor-neutral first)
1. **`agent-rules.md` Working Principles - the primary, all-agent home.** Add/absorb one proactive
   principle, e.g.: *"Before a design or change decision on non-obvious behavior, retrieve the prior
   reasoning first (`memory_search` for 'why was X / what was tried', or read the specific entry):
   inherit rejected alternatives, constraints, deferred items, and landmines rather than re-deriving
   them. Files are authority for what is true now; memory is authority for why - never substitute
   one for the other."* Fold it into the existing retrieval principle rather than net-adding a line
   (the file is at its startup-contract line budget - see Constraints).
2. **`history_retrieval.md` - add the proactive trigger to the mechanics skill.** Its trigger list is
   currently "when prior decisions/reason matter"; add the explicit *before design/change* trigger and
   a short "why vs. current-state" division-of-labor note, so the skill an agent loads for retrieval
   mechanics also tells it *when* to reach for them.
3. **Developer persona (`.agents/developer.md` + seed) - role sharpening.** The design/change-heavy
   role restates it as a standing habit ("before touching non-obvious code, ask 'has this been decided
   or tried before?'"). The base rule stays vendor-neutral in agent-rules; the persona only sharpens.
4. **Seed twins - the portability fix.** Every edit above lands in both the live `.memory-seed/**` and
   the `memory_seed/seed/.memory-seed/**` twin (and `.agents/` seed persona), so every downstream
   project and every agent inherits it. `esr` seed-twin drift keeps them in sync.
5. **Retire the Claude-personal note.** Once the seeded rule exists, delete or reduce
   `~/.claude/.../feedback_consult_memory_for_why.md` to a pointer, so the seeded control-plane rule is
   the single source of truth (no Claude-only divergence).

## Constraints (must address, not ignore)
- **Line budget:** `agent-rules.md` is governed by a startup-contract line-count test and is at/near
  the cap. The new principle must be **folded into an existing bullet or compressed elsewhere**, not
  appended - or the budget is consciously raised in the same change with the test updated. Verify the
  exact number against the test before editing.
- **Change-permission model:** `agent-rules.md` is a locked control-plane file editable only for
  "memory workflow / control-plane changes" - this proposal is exactly that, and is user-requested, so
  it qualifies; note it in the session entry.
- **Enforcement honesty:** agent *behavior* (retrieve-before-design) cannot be fully tool-gated - you
  cannot force a search. The levers are the contract (agent-rules), the skill trigger, and the persona,
  **backstopped** by each host's retrieval reminder (Claude's `UserPromptSubmit` "MEMORY RETRIEVAL
  REMINDER" already fires every turn). A tooling *nudge* - e.g. a hook that suggests retrieval before a
  flagged risky/irreversible operation - is a possible follow-on, not part of this proposal.

## Phases
1. Sharpen `agent-rules.md` Working Principles (fold, within budget) + seed twin; update the
   startup-contract test if the budget is raised.
2. Add the proactive trigger + why-vs-current-state note to `history_retrieval.md` (+ seed twin) and
   `skills/index.md` if a trigger-registry line is warranted.
3. Sharpen the developer persona (`.agents/developer.md` + seed persona).
4. Retire/point the Claude-personal memory note at the seeded rule.

## Acceptance criteria
- The proactive "retrieve the why before design/change" habit is stated once in vendor-neutral
  `agent-rules.md` Working Principles, mechanics in `history_retrieval.md`, and sharpened in the
  developer persona - all with synced seed twins (`esr` shows no drift).
- The files-for-now / memory-for-why division is explicit and not contradictory across those surfaces.
- `agent-rules.md` stays within (or consciously updates) its line-budget test.
- No Claude-only divergence: the seeded rule is authoritative; the personal note is retired or a pointer.
- Non-goal preserved: no attempt to force retrieval via a hard gate; behavior is contract + trigger +
  host reminder, with any tooling nudge deferred.

## Non-goals
- No new lazy skill for this (superseded by the "Working Principles over a new skill" decision).
- No always-search-memory mandate (wasteful); the trigger is *non-obvious design/change*, not every
  file read.
- No hard tool-gate on agent reasoning in this proposal.
