---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - documentation
  - proposal-lifecycle
  - control-plane
---

# Seeded document lifecycle control plane for the planning profile

Status: **PROPOSED** (2026-07-15). Inbox; not approved for implementation.
Priority: P2 - first prove the local document-lifecycle tooling, then extract it.
Source: JNL's question about shipping docs and document-management surfaces with Memory Seed, followed by
the 2026-07-15 review recorded in session entry `mse_wew6nkxc92b2en4k`.

## Problem

The optional `planning` profile currently installs `proposal_lifecycle.md` and creates four empty anchors:
`docs/inbox/`, `docs/todo/`, `docs/todo/completed/`, and `docs/reference/`. That teaches the workflow but
does not give a new project a usable human front door, outcome-specific lifecycle lanes, reusable document
shapes, generated indexes, or drift validation.

This repository is proving a richer folder-primary model, but its numbered paths, Constitution, roadmap,
Memory Trace plans, and historical corpus are project state. Copying those documents into every initialized
repository would turn local governance into accidental global policy.

## Proposal

Expand the existing `planning` profile into an opt-in, project-neutral document lifecycle control plane.
The package may always expose the generic commands, but project-local docs surfaces appear only when the
profile is selected or an existing repository explicitly adopts them.

### Fresh-project scaffold

Create deploy-once, unnumbered, generic surfaces:

```text
docs/
  README.md
  inbox/
  todo/
  spec/
    draft/
    deprecated/
  reference/
    archived/
  completed/
  rejected/
  superseded/
  deferred/
```

- `docs/README.md` is a small human-authored front door explaining that folder location is lifecycle state.
- The profile includes minimal proposal, plan, and candidate-spec templates without project-specific content.
- Shipped, rejected, superseded, and deferred outcomes remain distinct and discoverable.
- Generated lane indexes render secondary YAML such as priority, next action, blocking, and successor pointers.

### Management surfaces

- `memory-seed docs index`: rebuild per-lane tables and the generated roll-up in `docs/README.md`.
- `memory-seed docs check`: validate required lane metadata, pointer resolution, side-folder policy, and
  generated-index freshness.
- An explicit adoption/migration flow for repositories that already have `docs/`; it must preview changes
  before applying them and must never infer destructive moves.
- Profile state remains in `.memory-seed/project.yaml`; lane paths must be configurable rather than hardcoded
  to this repository's numbered taxonomy.

## Ownership and update rules

1. Scaffold files are deploy-once and become project-owned immediately.
2. `memory-seed update` never overwrites, silently reorganizes, or repopulates removed project docs.
3. A later schema expansion is an explicit `docs adopt`/migration decision, not update-time folder creation.
4. Markdown and YAML remain authoritative. Indexes and roll-ups are derived and fully rebuildable.
5. Existing repositories may keep their taxonomy; the checker reads project-local configuration/front-door
   authority instead of assuming the generic defaults.

## Constitution contribution

- **Capture:** gives proposals and source material explicit intake lanes and reusable document shapes.
- **Validation:** `docs check` makes lifecycle and pointer drift visible without changing content.
- **Retrieval:** generated lane indexes provide a deterministic human and agent read surface.
- **Trust:** outcome-specific lanes preserve rejected and superseded reasoning instead of deleting it.
- **Application:** the opt-in planning profile turns reusable lifecycle guidance into a working project surface.

Invariant guards: local files remain user-owned; history is superseded rather than erased; current docs remain
the authority for current state while session memory records why; behavior is agent/model independent; generated
indexes never become a second source of truth.

## Dependencies and rollout

1. Complete and validate the local `document-lifecycle-system-plan.md` Phase 2 (`docs index` and `docs check`).
2. Separate generic lane/schema behavior from this repository's numbered paths and allowlist.
3. Add fresh-init, existing-docs adoption, update, removal, and idempotency tests.
4. Dogfood the generic profile in a clean temporary project and a repository with an established docs tree.
5. Only then replace the current four-anchor planning scaffold.

## Non-goals

- Do not add document lifecycle scaffolding to Memory Seed's default core profile.
- Do not seed this repository's `CONSTITUTION.md`, numbered lane names, roadmap, plans, specs, references, or
  completed history.
- Do not make generated indexes authoritative or require a database, server, network, or hosted service.
- Do not silently migrate existing `docs/todo/completed/` projects when Memory Seed updates.

## Acceptance criteria

- A fresh planning-profile project has a readable lifecycle front door and complete generic lane set.
- `docs index` is deterministic and rebuildable from Markdown/YAML.
- `docs check` catches missing metadata, dangling pointers, invalid side folders, and stale generated blocks.
- Init/update/adoption tests prove existing project docs are not overwritten or moved without explicit approval.
- Removing the planning profile removes only empty Memory Seed-created anchors; user-authored docs survive.
- Seed/live parity and the full Memory Seed validation suite pass.
