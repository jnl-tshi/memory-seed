---
memory-system-version: 2.16
tags:
  - memory-seed
  - skill
  - proposal-lifecycle
---

# Proposal Lifecycle Skill

Use this skill when triaging proposal, research, or task documents through a project's docs
lifecycle folders.

## Purpose

Keep planning material in a simple lifecycle:

```text
inbox -> todo -> completed
inbox -> reference
```

Path conventions are project-local:

- This repository uses the numbered taxonomy: `docs/1_Inbox/`, `docs/2_Todo/`,
  `docs/2_Todo/completed/`, `docs/3_Spec/`, and `docs/4_Reference/`.
- Fresh projects created by the planning profile may use the generic bootstrap taxonomy:
  `docs/inbox/`, `docs/todo/`, `docs/todo/completed/`, and `docs/reference/`.

In either taxonomy, the inbox is for unassessed source material, todo is for refined active plans,
completed is for implemented/rejected/superseded/resolved plans, spec is for live normative
contracts, and reference is for source research, audits, market scans, extracted learnings, and
other material that informs proposals but is not itself an actionable proposal.

## Lifecycle Rules

1. Resolve the active project's lifecycle paths before moving files. Prefer numbered paths when the
   project already has `docs/1_Inbox/`; otherwise use the generic bootstrap paths.
2. Do not leave an accepted actionable proposal in the inbox. Promote it into a refined todo plan
   with status, priority, scope, non-goals, dependencies, acceptance criteria, and provenance.
3. Move completed, rejected, or superseded proposal files into the completed folder. Keep the
   final disposition near the top of the file.
4. Do not move a partially complete plan to completed unless the remaining work is explicitly split
   into a new active proposal or recorded as a deferred follow-up.
5. Do not create nested lifecycle folders such as `docs/inbox/todo/`,
   `docs/todo/completed/todo/`, or `docs/1_Inbox/2_Todo/`. Repair those by restoring the top-level
   lifecycle path.
6. Preserve source context when refining: either include the important evidence in the refined plan
   or move source-only material to the reference folder with clear provenance.
7. Prefer one canonical active proposal per workstream. Companion research or synthesis documents
   can remain in todo only when they still inform an open decision.

## Required Status Block

Every promoted proposal should declare:

```text
Status:
Priority:
Source:
Scope:
Non-goals:
Dependencies:
Acceptance criteria:
```

Use explicit dates when marking shipped, rejected, or superseded work.

## Update Surfaces

When moving or resolving proposals, check whether these need updates:

- `docs/2_Todo/0_NEXT_STEPS.md` or `docs/todo/NEXT_STEPS.md`
- `docs/3_Spec/functionality-audit.md` or `docs/spec/functionality-audit.md`
- `CHANGELOG.md` when release-facing behavior changed
- `.memory-seed/index.md` when active architecture or project state changed
- `.memory-seed/sessions/YYYY-MM-DD.md` for the durable decision log
- Markdown links that pointed at the old path

## Completion Criteria

A proposal can move to the completed folder when one of these is true:

- the planned implementation shipped or is fully present in unreleased changes;
- the proposal was explicitly rejected, with rationale;
- the proposal was superseded by a newer canonical plan;
- the document is a source report whose actionable recommendations were split into canonical active
  or completed proposals.

If any material work remains, leave the document active or create a follow-on plan before moving it.

## Verification

After lifecycle edits, run the smallest useful checks:

```text
rg "<old-path-or-filename>" docs .memory-seed memory_seed tests
python -m memory_seed.cli links check
python -m memory_seed.cli doctor
```

For seed or registry changes, also run the relevant unit tests that cover seed inventory and live/seed
parity.
