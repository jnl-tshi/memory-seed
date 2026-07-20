---
title: Memory Seed semantic record and signal foundation
status: active
priority: P1
next_action: Prove the append-only ADR sidecar contract on three existing decisions after B0b Trail parity and the BG1 provenance crosswalk.
blocked_by:
  - React Trail parity and B0b acceptance
  - memory-provenance-and-authority-taxonomy-proposal.md
  - memory-quality-metrics-v0-proposal.md
sources:
  - ../7_Superseded/memory-seed-typed-entries-adr-sidecar-proposal.md
  - ../7_Superseded/memory-signal-hierarchy-exploration.md
spec_binding: ../3_Spec/draft/adr-lifecycle-sidecar-contract.md
---

# Semantic Record and Signal Foundation

Status: **ACTIVE, BLOCKED BY NAMED GATES**. This plan owns explicit decision identity, ADR lifecycle,
and the inspectable signals that may later influence retrieval.

## Outcome

Give Memory Seed a small, high-signal decision corpus without rewriting chronological history or making a
database authoritative. An ADR sidecar is the canonical record of ADR promotion, identity, and lifecycle;
the referenced entries remain canonical for rationale and evidence.

Five-question test: **Capture**, **Retrieval**, and **Trust**.

## Authority boundary

| Concern | Canonical owner |
|---|---|
| What was recorded at the time | Original append-only session entry |
| ADR promotion, stable identity, and lifecycle | One append-only Markdown ADR sidecar |
| Why a lifecycle transition occurred | Referenced `decision-update` entry |
| Current ADR status | Derived from the latest valid sidecar transition |
| Current implementation truth | Current project files and live specs |
| Search index, registry, or Trace view | Rebuildable projection |

This is partitioned authority, not dual authority: each field has one declared owner.

## Scope

1. Adopt the candidate ADR sidecar contract and shared validator.
2. Promote three existing real-corpus decisions without editing their source entries.
3. Add deterministic CLI and MCP operations for promotion and transition through one shared core.
4. Expose ADR identity, lifecycle, topic, provenance, and source references before changing ranking.
5. Evaluate a deliberately small `record_kind` vocabulary for **new tool-created records only**.
6. Run a real-corpus retrieval comparison before any decision signal affects default ordering.

## Non-goals

- No historical entry migration or inferred reclassification.
- No authoritative YAML snapshot, mutable `current_status`, or manually maintained registry.
- No generic workflow/event-sourcing framework.
- No new graph edge kinds; canonical entry edges remain `related_entries`, `supersedes`, and `evolves`.
- No automatic ADR promotion or confidence-to-authority upgrade.

## Implementation sequence

### Phase 1 - ADR walking skeleton

- Adopt `docs/3_Spec/draft/adr-lifecycle-sidecar-contract.md` as the candidate contract. **Its decision
  identity was amended 2026-07-20**: a decision is the pair `(source_entry_id, source_decision)`, the
  ordinal derived from the DRAFT grammar with a singular `### Decision` read as `d1`. The sidecar no
  longer invents a decision key, heading path, or source-text fingerprint — so this phase implements a
  pointer, not an identity scheme.
- Promote three decisions spanning a direct decision entry, a multi-decision entry, and a legacy entry.
- Prove exact source resolution, append-only transition order, and full context retrieval.
- **Also measure, added 2026-07-20:** ambiguity reduction against authoring cost. This phase *is* step 2
  of the corrected pre-triage sequence in [INBOX-ASSESSMENT.md](../1_Inbox/INBOX-ASSESSMENT.md) — same
  three decisions, same contract, same decision-level identity — so step 2 discharges here rather than as
  separate work. The natural subject is the entry-level supersession collateral recorded in
  `mse_mkxdvaxvw99dz4s0`, and the natural target shape is the contract's own `source_decision` anchor.
- **Record eligibility, not just outcome** *(crosswalk delta 3/10, adversarially verified)*: when a record
  is evaluated and found **not to need** a sidecar, say so. Today `classify_pending` means "undecided",
  which is not the same claim. The vocabulary already exists and is proven — `memory_seed/quality.py:35`
  ships `measured | not_applicable | unavailable`, and its own comment draws exactly this line
  ("`unavailable` — the input does not exist yet — rather than `not_applicable`, which would claim we
  looked and found an empty population"). This is extending a proven pattern to record level, not a new
  design.

### Phase 2 - Deterministic writers and integrity

- Implement shared `promote_decision`, `transition_adr`, `supersede_adr`, and validation operations.
- Require expected-state optimistic concurrency for transitions.
- Detect missing source/update entries, invalid transitions, competing heads, and malformed sidecars.
- Keep repair explicit; validators never silently rewrite the ledger.

### Phase 3 - Semantic records

- Evaluate `record_kind` for new records after authoring support exists.
- Leave historical records `legacy`/unclassified unless a human explicitly promotes a decision.
- Keep kind, topic, provenance, authority, lifecycle, confidence, and actionability as separate fields.

### Phase 4 - Signal exposure and validation

- Surface signals as inspectable metadata in CLI, MCP, and Trace.
- Compare signal-off and signal-on retrieval over the full corpus with unaffected controls.
- Promote a ranking change only through the existing ranking A/B gate.

## Acceptance criteria

- A decision in an immutable historical entry can be promoted without modifying that entry.
- ADR identity and lifecycle are readable from one append-only Markdown sidecar.
- Every transition resolves to a decision-update entry containing attributable rationale.
- `current_status` is computed, never duplicated as authoritative state.
- Sidecar loss is reported as missing authored memory, not silently reconstructed as if promotion occurred.
- All indexes and Trace views rebuild from repository Markdown.
- Legacy retrieval remains complete and superseded history remains discoverable.
