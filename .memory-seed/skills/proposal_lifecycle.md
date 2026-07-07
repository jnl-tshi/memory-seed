---
memory-system-version: 2.16
tags:
  - memory-seed
  - skill
  - proposal-lifecycle
---

# Proposal Lifecycle Skill

Use this skill when triaging proposal, research, or task documents through `docs/inbox/`,
`docs/todo/`, `docs/todo/completed/`, and `docs/reference/`.

## Purpose

Keep planning material in a simple lifecycle:

```text
inbox -> todo -> completed
inbox -> reference
```

`docs/inbox/` is for unassessed source material. `docs/todo/` is for refined active plans.
`docs/todo/completed/` is for implemented, rejected, superseded, or otherwise resolved plans.
`docs/reference/` is for source research, audits, market scans, extracted learnings, and other
reference material that informs proposals but is not itself an actionable proposal.

## Lifecycle Rules

1. Do not leave an accepted actionable proposal in `docs/inbox/`. Promote it into a refined
   `docs/todo/*.md` plan with status, priority, scope, non-goals, dependencies, acceptance criteria,
   and provenance.
2. Move completed, rejected, or superseded proposal files into `docs/todo/completed/`. Keep the
   final disposition near the top of the file.
3. Do not move a partially complete plan to completed unless the remaining work is explicitly split
   into a new active proposal or recorded as a deferred follow-up.
4. Do not create nested lifecycle folders such as `docs/inbox/todo/` or `docs/todo/completed/todo/`.
   Repair those by restoring the top-level lifecycle path.
5. Preserve source context when refining: either include the important evidence in the refined plan
   or move source-only material to `docs/reference/` with clear provenance.
6. Prefer one canonical active proposal per workstream. Companion research or synthesis documents
   can remain in `docs/todo/` only when they still inform an open decision.

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

- `docs/todo/NEXT_STEPS.md`
- `docs/spec/functionality-audit.md`
- `CHANGELOG.md` when release-facing behavior changed
- `.memory-seed/index.md` when active architecture or project state changed
- `.memory-seed/sessions/YYYY-MM-DD.md` for the durable decision log
- Markdown links that pointed at the old path

## Completion Criteria

A proposal can move to `docs/todo/completed/` when one of these is true:

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
