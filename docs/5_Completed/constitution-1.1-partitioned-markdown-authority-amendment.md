---
title: Constitution 1.1 partitioned Markdown authority amendment
status: completed
completed: 2026-07-16
ratified_by: JNL
---

# Constitution 1.1 - Partitioned Markdown Authority

Status: **RATIFIED 2026-07-16**.

## Amendment

Clarify Invariant 6 so authoritative memory may be distributed across append-only primary Markdown entries
and narrowly scoped Markdown sidecars. Each authoritative field or lifecycle must have one declared owner.
Indexes, caches, databases, computed snapshots, and UI projections remain derived and rebuildable.

## Reason

An ADR sidecar is a higher-signal canonical record of decision promotion and lifecycle than repeated semantic
inference over chronological entries. Keeping the sidecar append-only and Markdown-native preserves local
ownership, human readability, attribution, and the separation between current implementation truth and
historical reasoning.

## Boundaries

- This amendment does not permit arbitrary authoritative YAML, databases, or hosted state.
- Narrative rationale and evidence stay in referenced entries.
- Current project files and live specifications remain authoritative for implementation truth.
- A sidecar may own only the fields explicitly assigned by its adopted contract.

## Ratification

JNL accepted this model on 2026-07-16 after comparing a derived-only registry with an authoritative ADR
sidecar. The adopted implementation direction is the append-only Markdown ledger defined by the draft ADR
lifecycle sidecar contract.
