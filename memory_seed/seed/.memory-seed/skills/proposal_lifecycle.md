---
memory-system-version: 2.19
tags:
  - memory-seed
  - skill
  - proposal-lifecycle
---

# Proposal Lifecycle Skill

Use this skill when triaging proposal, research, or task documents through a project's docs lifecycle.

## Purpose

**The folder a document lives in IS its lifecycle state** — a person browsing the tree sees the state of
everything without opening files or scanning YAML. Keep planning material moving through distinct lanes,
and give each *outcome* its own lane instead of one mixed archive:

```text
inbox -> todo -> completed     (shipped / applied)
              -> rejected      (declined; kept for the why-not)
              -> replaced    (replaced; points to its successor)
              -> deferred      (parked / long-horizon)
inbox -> reference             (source material; -> reference/archived once mined)
spec:  draft -> live           (contracts; -> deprecated when retired)
```

**The project's `docs/README.md` front door is the authority for the exact lane paths — read it first.**

Path conventions are project-local:

- This repository uses the numbered taxonomy with promoted terminal lanes: `docs/1_Inbox/`,
  `docs/2_Todo/`, `docs/3_Spec/` (+ `draft/`, `deprecated/`), `docs/4_Reference/` (+ `archived/`),
  `docs/5_Completed/`, `docs/6_Rejected/`, `docs/7_Replaced/`, `docs/8_Deferred/`.
- Fresh projects created by the planning profile may use the generic bootstrap taxonomy: `docs/inbox/`,
  `docs/todo/`, `docs/completed/`, `docs/reference/` (adding the disposition lanes when adopted).

In either taxonomy: inbox = unassessed source; todo = refined active plans (blocked items stay here,
flagged in YAML); each terminal lane names one **outcome** (completed=shipped, rejected=declined,
replaced=replaced, deferred=parked); spec = live normative contracts (candidates in `draft/`);
reference = source research/audits/scans (mined-out sources in `archived/`).

## Lifecycle Rules

1. **Folder is the state.** A document's lifecycle state is *where it lives*; any `Status:` prose must
   mirror the folder, never contradict it. Read the project's `docs/README.md` before moving files.
2. Do not leave an accepted actionable proposal in the inbox. Promote it into a refined todo plan with
   priority, next action, scope, non-goals, dependencies, acceptance criteria, and provenance.
3. **Route each outcome to its own lane — do not dump everything in "completed".** Shipped -> completed;
   declined -> rejected (kept, with a one-line reason); replaced -> replaced (with a pointer to the
   successor); parked -> deferred. Keep the disposition near the top of the file.
4. Do not move a partially complete plan to a terminal lane unless the remaining work is explicitly split
   into a new active proposal or recorded as a deferred follow-up.
5. Do not create nested lifecycle folders (`docs/inbox/todo/`, `docs/1_Inbox/2_Todo/`). Repair by
   restoring the top-level lane.
6. Preserve source context when refining: include the key evidence in the refined plan, or move
   source-only material to the reference lane (and to `reference/archived/` once its actionable items are
   extracted, recording `extracted_into`).
7. Prefer one canonical active proposal per workstream.
8. **Never `git rm` a rejected or replaced document — move it to its lane.** Deletion loses the why-not
   and the reasoning trail (mirrors the memory system's replace-don't-delete rule).

## Secondary metadata (what the folder can't show)

The folder carries the primary state; YAML frontmatter carries the rest — `priority`, `next_action`,
`blocked_by` (todo); `replaced_by` / `split_into`, `rejected_reason`, `extracted_into` (terminal /
reference); `spec_binding` (spec). A generated per-lane `README.md` index renders these into a human
table so no one has to scan YAML.

## Required disposition + metadata

Every promoted proposal declares, near the top: Status, Priority, Source, Scope, Non-goals,
Dependencies, Acceptance criteria. Use explicit dates when marking shipped, rejected, or replaced work.

## Update Surfaces

When moving or resolving proposals, check whether these need updates:

- the project's `docs/README.md` front door and the destination lane's index
- `docs/2_Todo/0_NEXT_STEPS.md` (or the project's next-steps brief)
- `docs/3_Spec/functionality-audit.md`
- `CHANGELOG.md` when release-facing behavior changed
- `.memory-seed/index.md` when active architecture or project state changed
- `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` for the durable decision log
- **every markdown link that pointed at the old path** — moving a doc across lanes breaks inbound links;
  grep (`rg`) and fix them in the same change

## Completion Criteria

Move out of `todo` when: the work shipped (-> completed); it was rejected with rationale
(-> rejected); it was replaced by a newer canonical plan (-> replaced, with a pointer); it is a
source report whose recommendations were split into canonical proposals (the source stays in reference,
moved to `archived/`); or it is parked (-> deferred). If material work remains, leave it active or create
a follow-on plan first.

## Verification

After lifecycle edits, run the smallest useful checks:

```text
rg "<old-path-or-filename>" docs .memory-seed memory_seed tests   # catch broken links after a move
python -m memory_seed.cli links check
python -m memory_seed.cli doctor
```

(A `memory-seed docs check` that validates lane membership and required per-lane metadata is planned.)
For seed or registry changes, also run the unit tests that cover seed inventory and live/seed parity.
