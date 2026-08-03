---
title: Memory Seed semantic record and signal foundation
status: active
priority: P1
next_action: Evaluate the remaining record_kind and retrieval-signal work after the provenance and quality gates; the living ADR foundation shipped 2026-08-03.
blocked_by:
  - memory-provenance-and-authority-taxonomy-proposal.md
  - memory-quality-metrics-v0-proposal.md
sources:
  - ../7_Replaced/memory-seed-typed-entries-adr-sidecar-proposal.md
  - ../7_Replaced/memory-signal-hierarchy-exploration.md
spec_binding: ../3_Spec/adr-lifecycle-sidecar-contract.md
---

# Semantic Record and Signal Foundation

Status: **ACTIVE FOR PHASES 3-4**. The living ADR foundation and deterministic writers shipped and were
dogfooded on 2026-08-03; the remaining semantic-record and retrieval-signal work stays blocked by the named
provenance and quality gates.

## Outcome

Give Memory Seed a small, high-signal decision corpus without rewriting chronological history or making a
database authoritative. An ADR sidecar is the canonical record of architectural-concern membership, its
curated Decision/Why/Evolution synopsis, revision ledger, and governing head; referenced session decisions
remain the detailed evidence authority.

Five-question test: **Capture**, **Retrieval**, and **Trust**.

## Authority boundary

| Concern | Canonical owner |
|---|---|
| What was recorded at the time | Original append-only session entry |
| ADR concern membership, curated synopsis, and lifecycle | One append-only Markdown ADR sidecar |
| Detailed evidence and rationale for a referenced decision | Original append-only session entry |
| Why an ADR revision or no-change review occurred | The ledger event synopsis plus its referenced update entry |
| Current ADR status and governing head | Derived by replaying accepted ledger revisions |
| Current implementation truth | Current project files and live specs |
| Search index, registry, or Trace view | Rebuildable projection |

This is partitioned authority, not dual authority: each field has one declared owner.

## Scope

1. **Delivered 2026-08-03:** adopt the living ADR sidecar contract and shared validator.
2. **Delivered 2026-08-03:** dogfood three real architectural concerns without editing source entries.
3. **Delivered 2026-08-03:** add deterministic CLI/MCP operations and the mandatory MCP review gate.
4. **Delivered 2026-08-03:** expose ADR identity, lifecycle, provenance, references, API, and Trace workspace.
5. Evaluate a deliberately small `record_kind` vocabulary for **new tool-created records only**.
6. Run a real-corpus retrieval comparison before any decision signal affects default ordering.

## Non-goals

- No historical entry migration or inferred reclassification.
- No authoritative YAML snapshot, mutable `current_status`, or manually maintained registry.
- No generic workflow/event-sourcing framework.
- No new graph edge kinds; canonical entry edges remain `related_entries`, `supersedes`, and `evolves`.
- No automatic ADR promotion or confidence-to-authority upgrade.

## Implementation sequence

### Phase 1 - Living ADR walking skeleton — SHIPPED 2026-08-03

- Adopted `docs/3_Spec/adr-lifecycle-sidecar-contract.md` as the live contract. Decision identity remains
  `(entry_id, dN)`, but the implemented sidecar is one living record per architectural concern rather than
  the retired pointer-only prototype.
- Dogfooded three concerns spanning multi-revision history, one decision shared by two ADRs, and a converging
  predecessor chain.
- Proved exact source resolution, append-only replay, mandatory review of any lineage member, and full context
  retrieval without rewriting historical entries.
- **Also measure, added 2026-07-20:** ambiguity reduction against authoring cost. This phase *is* step 2
  of the corrected pre-triage sequence in [INBOX-ASSESSMENT.md](../4_Reference/INBOX-ASSESSMENT.md) — same
  three decisions, same contract, same decision-level identity — so step 2 discharges here rather than as
  separate work. The natural subject is the entry-level supersession collateral recorded in
  `mse_mkxdvaxvw99dz4s0`, and the natural target shape is the contract's canonical `decision_ref`.
- **Record eligibility, not just outcome** *(crosswalk delta 3/10, adversarially verified)*: when a record
  is evaluated and found **not to need** a sidecar, say so. Today `classify_pending` means "undecided",
  which is not the same claim. The vocabulary already exists and is proven — `memory_seed/quality.py:35`
  ships `measured | not_applicable | unavailable`, and its own comment draws exactly this line
  ("`unavailable` — the input does not exist yet — rather than `not_applicable`, which would claim we
  looked and found an empty population"). This is extending a proven pattern to record level, not a new
  design.

### Phase 2 - Deterministic writers and integrity — SHIPPED 2026-08-03

- Implemented shared promote, revise, transition, replay, review, and validation operations.
- Expected-head optimistic concurrency, cycle detection, and competing-head rejection are enforced.
- CLI writers and read-only MCP tools share the same core; `memory_session_append` remains the fail-closed
  transactional MCP backstop.
- Structural branch reconciliation preserves independent events, deduplicates exact repeats, and reports
  divergent IDs or competing acceptances as conflicts.
- **Branch-safe integration, noted 2026-07-20 — follow the link-sidecar pattern.** Link sidecars were
  silently discarded by `session merge-branch`: the sessions-tree fuse's base-reset loop diffed and reset
  every path under `.memory-seed/sessions`, but the classifier that decides what the fuse can rebuild
  didn't recognize `sessions/links/**`, so a branch-side edit vanished with no error. The fix (this
  session) generalizes the fuse to a third sidecar kind exactly as diagram sidecars were the first, and
  adds a defense-in-depth guard — `_is_recognized_session_tree_path` in `memory_seed/core.py` — that
  refuses to reset any session-tree path no classifier recognizes, rather than silently discarding it.
  The implemented `.memory-seed/decisions/<adr_id>.md` reconciliation follows that requirement: branch-authored
  events are structurally fused, never reset to base text, and explicit conflicts stop integration.

### Phase 3 - Semantic records

- Evaluate `record_kind` for new records after authoring support exists.
- Leave historical records `legacy`/unclassified unless a human explicitly promotes a decision.
- Keep kind, topic, provenance, authority, lifecycle, confidence, and actionability as separate fields.

### Phase 4 - Signal exposure and validation

- Surface signals as inspectable metadata in CLI, MCP, and Trace.
- Compare signal-off and signal-on retrieval over the full corpus with unaffected controls.
- Promote a ranking change only through the existing ranking A/B gate.

## Acceptance criteria

The ADR-specific criteria below passed on 2026-08-03. Phases 3-4 retain their own signal/ranking gates.

- A decision in an immutable historical entry can be promoted without modifying that entry.
- ADR identity and lifecycle are readable from one append-only Markdown sidecar.
- Every event's `update_entry_id` resolves to an existing session entry; proposals and no-change reviews
  carry the concise ADR-owned rationale their event types require.
- `current_status` is computed, never duplicated as authoritative state.
- A missing `.memory-seed/decisions/` directory is a valid empty ADR corpus; existing sidecars are validated
  and never reconstructed from sessions as if promotion had occurred.
- All indexes and Trace views rebuild from repository Markdown.
- Legacy retrieval remains complete and superseded history remains discoverable.
