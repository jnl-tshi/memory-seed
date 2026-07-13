---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - documentation
  - lifecycle
status: proposed
---

# Document lifecycle system — front door, controlled status, explicit lanes, drift-checkable

Status: **PROPOSED** (2026-07-13). Inbox.
Priority: P2 — knowledge-base hygiene; mostly a doc + a small validator, no runtime change.
Source: Objective review of `docs/` (agent, 2026-07-13) + user's own gap analysis the same day. This plan
is the synthesis of both.

## Goal

Give `docs/` the same lifecycle rigor the project already gives *session memory* (controlled status,
supersede-don't-delete, an integrity check). The folder **structure is sound**; what's missing is a
defined lifecycle, a single machine-readable status, explicit lanes for the states that currently have
nowhere to live, and a check that keeps folder and status from drifting apart.

## Synthesized gaps → fixes (both reviews)

| # | Gap | Raised by | Fix (this plan) |
|---|---|---|---|
| 1 | No root docs map / lifecycle undocumented (no `docs/README.md`) | both | §1 front door |
| 2 | Status is free-text prose, drifts; folder ≠ status | agent | §2 controlled `status:` + §6 drift check |
| 3 | Spec mixes live/binding and proposed/draft contracts | user | §3 spec binding-status (`live/draft/candidate/deprecated`) |
| 4 | No deferred/parked lane — paused ideas look untriaged or active | user | §2 `status: deferred` inside Todo (folder stays flat) |
| 5 | Completed is a mixed archive (shipped/rejected/superseded/source) | both | §4 required terminal **disposition** |
| 6 | Todo has no priority/state separation | both | §5 required `priority` / `blocked_by` / `next_action` |
| 7 | Reference lane under-recognized (source material has a home) | user | §5 Reference role + extraction rule |
| 8 | Side folders (`superpowers/`, `2_Todo/{Claude,codex}/`) undocumented | both | §7 side-folder allowlist rule |
| 9 | Numbering conflates workflow-stage with document-type | agent | §1 front door names *flow lanes* vs *type lanes* |
| 10 | Docs disconnected from session-memory graph | agent | §8 optional `entries:` back-reference (phase 4) |

Three **live drifts** the review already surfaced, fixed in migration: `proactive-history-retrieval-discipline-proposal.md`
says `PROPOSED` but shipped; `freshness-aware-memory-ranking-proposal.md` says `LANDED` but sits in Todo;
`configurable-integration-mode-plan.md` says `PROPOSED` but P0.1 shipped.

## Plan

### 1. Front door — `docs/README.md`
One page that is the missing map: the lanes, what each is for, the promotion rules, what "done" means,
the naming convention, and the side-folder rule. It states the **stage vs type** distinction explicitly:

- **Flow lanes** (a doc moves through these): `1_Inbox → 2_Todo → 2_Todo/completed`.
- **Type lanes** (durable; a doc *enters* one when relevant, it is not a "later stage"): `3_Spec`
  (normative contracts), `4_Reference` (source material). Unifies the existing `3_Spec/README.md` and
  `4_Reference/README.md` under one root.

### 2. Controlled `status:` frontmatter — one machine-readable source of truth
Standardize the field that **already exists** on some specs (`status: "proposed-specification"`). Values
are scoped by lane:

| Lane | `status:` values | Required companions |
|---|---|---|
| `1_Inbox` | `inbox` | — |
| `2_Todo` | `proposed` · `approved` · `in-progress` · `deferred` · `blocked` | `priority`, `next_action`, `blocked_by` (§5) |
| `2_Todo/completed` | `shipped` · `rejected` · `superseded` · `split` · `source-retained` | pointer: `superseded_by` / `split_into` / `implemented_by` (§4) |
| `3_Spec` | `live` · `draft` · `candidate` · `deprecated` | `deprecated_by` when deprecated (§3) |
| `4_Reference` | `active` · `archived` | `extracted_into` when archived (§5) |

The **status field is the source of truth**; the folder is derived from it and checked against it (§6),
which removes the current two-sources-that-disagree problem.

### 3. Spec binding-status (gap #3)
Every `3_Spec` file declares `status: live|draft|candidate|deprecated`. `3_Spec/README.md` is amended:
the folder holds specs at all four bindings, and only `live` is normative. The two current
`proposed-specification` files (`memory-trace-trail-search-and-graph-ux.md`,
`memory-trace-derived-artifact-provenance-contract.md`) become `candidate`. A `deprecated` spec stays in
place (never deleted) with `deprecated_by:` pointing at its successor.

### 4. Completed needs a disposition, not just presence (gap #5)
Every file in `completed/` carries a terminal `status`: `shipped` (implemented), `rejected` (declined —
kept for the *why-not*, **not** `git rm`'d), `superseded` (replaced — `superseded_by:` a doc/entry),
`split` (broken into others — `split_into:`), or `source-retained` (raw source whose actionable items
were folded elsewhere). This makes `completed/` a legible archive instead of a mixed bin, and gives
**rejected/superseded proposals a home** — mirroring the memory system's supersede-don't-delete rule
(the retracted orchestration proposal *should* have landed here as `rejected`, not been deleted).

### 5. Todo carries decision metadata; Reference has a defined role (gaps #4, #6, #7)
- **Todo (folder stays flat):** every file requires `priority: P0|P1|P2|P3`, `next_action:` (one line),
  and `blocked_by:` (id/none). `status: deferred` is the parked/long-horizon lane (no separate folder);
  `blocked` + `blocked_by` is the waiting lane. So "next implementation / approved-but-later / research /
  blocked / parked" are all readable from fields, not guessed from the pile.
- **Reference:** the lane for imported source material — market research, source learnings, screenshots,
  vendor reports. Rule: once a Reference doc's actionable items are extracted into a plan/spec, set
  `status: archived` with `extracted_into:` the target, so live source vs. mined-out source is distinct.

### 6. Drift check — `memory-seed docs check` (the enforcement)
A read-only validator, mirroring `links check`/`esr`, that fails/ warns on:
- a doc with no `status:` or a value invalid for its lane;
- **folder ≠ status** (a `shipped`/terminal doc outside `completed/`; a `live` spec's file marked
  `candidate`; the LANDED-in-Todo class);
- a terminal doc missing its required pointer; a spec with no binding; a todo missing
  `priority`/`next_action`; a file under a non-allowlisted side folder (§7).
Surfaced by `esr` and CI. This is the piece that makes the whole thing self-maintaining rather than a
recurring "doc coherence pass."

### 7. Side-folder rule (gap #8)
The front door carries an **allowlist** of legitimate non-lane folders with a one-line reason each
(e.g. per-folder `agent-templates/`, `memory-trace-phase0-baseline/`). `docs/superpowers/` and the
per-agent `2_Todo/{Claude,codex}/` folders must each be either documented (external mirror / temp agent
scratch → gitignore) or reconciled into a lane. `docs check` flags anything off the allowlist.

### 8. (Phase 4, optional) Wire docs to the memory graph
A `entries:` frontmatter back-reference from a doc to the session entries that created/approved/shipped
it, so the same graph that answers "why does this decision exist" answers "why does this doc exist / is
it still live." Closes the docs↔memory asymmetry.

## Migration (one pass, docs-only)
1. Fix the three live drifts: move `proactive-history-retrieval-discipline-proposal.md` and
   `freshness-aware-memory-ranking-proposal.md` → `completed/` as `shipped`; set
   `configurable-integration-mode-plan.md` → `in-progress`.
2. Set spec bindings on the seven `3_Spec` files; amend `3_Spec/README.md`.
3. Resolve `superpowers/` + `2_Todo/{Claude,codex}/` (document or reconcile).
4. Backfill `status:` on the rest incrementally; new docs require it from day one.

## Phasing
- **P1 (docs only):** front door + status vocabulary + fix the 3 drifts + spec bindings. High value, no code.
- **P2:** `memory-seed docs check` validator, into `esr` + CI.
- **P3:** backfill `status:` across existing docs.
- **P4 (optional):** `entries:` doc↔memory link + a Trace view of the doc lifecycle.

## Non-goals
- No folder restructure — the PARA-ish structure is sound; this adds status + a front door + a check.
- Todo stays flat (deferred/blocked are statuses, not folders).
- No big-bang backfill — the check warns; adoption is incremental, enforced for new docs first.

## Relationship to existing coverage (checked)
- Mirrors the **session-memory lifecycle** (`supersedes`/`evolves`, `links check`, `esr`) — this applies
  the same discipline to docs, which today have none of it.
- Standardizes the **existing partial** `status: "proposed-specification"` frontmatter convention.
- Unifies `docs/3_Spec/README.md` + `docs/4_Reference/README.md` under a root `docs/README.md`.
- Complements `docs/2_Todo/0_NEXT_STEPS.md` (a hand-maintained brief) with a *derivable* status the
  check can verify, rather than a second prose tracker.
