---
memory-system-version: 2.15
tags:
  - memory-seed
  - proposal
  - related-entries
  - graph
  - mutation
---

# Related Entries P2 Mutation Plan

> **Status:** ACTIVE - approved 2026-07-05.
> **Priority:** P4 mutation/convenience work. It is unblocked by user sign-off, but should run after
> the lower-risk Memory Trace retrieval-service extraction and decision-diagram convention
> work unless the user explicitly reprioritizes graph curation.
> **Source:** User decision 2026-07-05: implement Related-entries P2, including backfill between older
> entries and the optional `memory-seed link add` helper.
> **Scope:** Add controlled mutation helpers for explicit `related_entries` curation while preserving
> append-only session-entry semantics.
> **Non-goals:** No silent rewriting of historical entry prose. No automatic graph generation. No
> Memory Trace write/curation UI. No ranking changes. No sidecar graph store unless the in-entry approach
> proves insufficient during implementation.
> **Boundary with the evolution-edges seeding pass (reconciled 2026-07-10):** the two mechanisms
> are complementary and must not blur. The lineage seeding pass in
> [`evolution-edges-plan.md`](evolution-edges-plan.md) writes **new** clarification entries that
> declare typed `evolves`/`supersedes`/`continuity` against old entries - zero bytes of history
> change, no mutation machinery needed. This plan's backfill mutates **existing** old entries'
> YAML for untyped `related_entries` only. Typed lifecycle history always goes through the seeding
> pass; this plan never writes `evolves`/`supersedes`/`continuity` into historical entries.
> **Dependencies:** P1 related-entry graph surfaces are shipped in 2.13.0; `links check` already
> validates dangling `related_entries` across both session layouts.
> **Acceptance criteria:** see below.

## Decision

Build P2 mutation helpers for explicit related-entry curation:

1. `memory-seed link add <target_entry_id> [--from <entry_id>]` for current/newest-entry forward
   links.
2. A deliberate backfill workflow for two pre-existing entries, with visible user intent and
   validation.

The default writer should remain conservative: adding a relation to the current/newest entry is the
normal path because it does not rewrite history. Backfill between older entries is allowed only as an
explicit user-approved curation operation, not as an automatic suggestion writer.

## Proposed Behavior

### `link add` Current/Newest Entry

```text
memory-seed link add <target_entry_id> [--from <entry_id>]
```

- Default `--from` is the newest entry in the active session target.
- Refuse by default if `--from` is not the newest entry.
- Resolve both `--from` and target IDs before writing.
- Fail immediately on unknown IDs, self-links, or malformed IDs.
- Add `related_entries:` to the entry YAML block when absent.
- Deduplicate existing links and preserve existing order.
- Run or reuse the same validation logic as `links check` after writing.

### Backfill Between Older Entries

Backfill is allowed, but it must be explicit:

- require both source and target IDs;
- require a flag or command wording that makes historical curation obvious, such as
  `--allow-history-edit` or a dedicated `memory-seed link backfill <source> <target>`;
- create a backup before editing the session file;
- refuse ambiguous files, duplicate entry IDs, malformed YAML blocks, or entries without a safe
  fenced metadata block;
- update only the entry YAML metadata, never the prose body;
- remain idempotent.

Implementation should choose the smallest command surface that is easy to document and test. A
dedicated `link backfill` subcommand is acceptable if it makes the risk clearer than a flag on
`link add`.

## Non-Goals

- Do not automatically accept `link suggest` output.
- Do not edit reciprocal edges; read-time traversal already makes one directed edge visible from both
  entries.
- Do not introduce a `.memory-seed/links.yaml` sidecar in P2 unless direct metadata editing proves
  unsafe during implementation.
- Do not expose this as a Memory Trace UI write feature.
- Do not change MCP search ranking or default graph scoring.

## Acceptance Criteria

- `link add <target>` adds a deduplicated `related_entries` item to the newest/current entry and
  refuses unknown, malformed, self, or duplicate-dangerous IDs.
- Historical backfill requires explicit opt-in wording and creates a backup before editing.
- Backfill updates only entry YAML metadata, not entry prose or session ordering.
- Both writers are idempotent.
- `links check` passes after valid writes and fails with specific errors after invalid fixture writes.
- Tests cover flat sessions and per-user/day sessions where relevant.
- Docs and help text make the append-only exception clear.

## Provenance

- User sign-off 2026-07-05.
- Completed P1 source plan:
  [`completed/related-entries-generation-plan.md`](completed/related-entries-generation-plan.md).
- Current 3.0 coordination:
  [`3.0-plan.md`](completed/3.0-plan.md), [`NEXT_STEPS.md`](NEXT_STEPS.md).
