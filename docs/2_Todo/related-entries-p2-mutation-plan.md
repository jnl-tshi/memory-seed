---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - related-entries
  - graph
  - mutation
---

# Related Entries P2 Mutation Plan

> **Status:** RESOLVED 2026-07-17. `link add` shipped; backfill is **permitted but deliberately not a
> command** — see the procedure below.
>
> - **`link add` (current/newest entry) — SHIPPED.** Adding to the entry being authored does not rewrite
>   history, so it is clean under Invariant #2. Forward-only, idempotent, YAML-only, `links check`-gated.
> - **Backfill between older entries — RESOLVED by Constitution 1.2 (2026-07-17).** JNL chose to amend
>   Invariant #2 rather than reject the capability, but scoped it far tighter than this plan originally
>   proposed: *"this should not be part of the core functionality, it's a one-off procedure that needs to
>   be done with explicit user permission and gating of each item that will be added to the metadata."*
>
> **So there is no `memory-seed link backfill` command, and there should not be one.** A standing command
> is exactly what the amendment excludes: it would make one-off curation into core functionality, and a
> command that asks per-edge permission is a worse version of doing it by hand. The plan's original §
> "Backfill Between Older Entries" (flags, backups, idempotency) is **superseded** by the procedure below
> — it described a command shape the amendment does not permit.
>
> *(The retrieval-service extraction and decision-diagram work this plan was sequenced behind have both
> shipped.)*

## The sanctioned backfill procedure (one-off, per-edge approval)

Constitution 1.2 permits curating an **existing** entry's **untyped `related_entries`** only under all of
these at once. Any one failing means Invariant #2 applies unchanged and the edit must not happen.

**Before you start — is this the right tool at all?** The shipped
[evolution-edges seeding pass](../5_Completed/evolution-edges-plan.md) adds edges to history by writing a
**new** entry that declares them against old ones. History is untouched, and the graph reader computes the
inverse at read time, so the old entry shows the backlink anyway. **Prefer it.** Reach for curation only
when you specifically want an untyped `related_entries` pointer recorded on the old entry itself.

The procedure:

1. **Identify candidates** with `memory-seed link suggest --for <entry_id>` (read-only; ranks older
   entries and prints a paste-ready snippet). Never act on its output automatically — it ranks
   candidates, it does not decide.
2. **Present each proposed edge to the user individually**, with both entry titles and why they relate.
   One approval per edge. A blanket "yes, do them all" does not satisfy the amendment — per-item gating is
   the condition that makes this permissible.
3. **Edit by hand**, in the session file, adding only the approved id under `related_entries:` in that
   entry's YAML block. Touch nothing else. Never prose. Never `supersedes`/`evolves`/`continuity` — typed
   lifecycle edges in history go through the seeding pass, always.
4. **Verify** with `memory-seed links check` (dangling refs, forward-only, acyclic) and commit the edit on
   its own, with a message naming the user approval that authorised it.

**Do not automate any step of this.** If you find yourself scripting it, you have left the exception and
re-entered the invariant.
> **Priority:** convenience/mutation increment — Track A item 4 in [`0_NEXT_STEPS.md`](0_NEXT_STEPS.md);
> a `link add` (current-entry) + explicit historical backfill. Not a blocker; sequence after the
> Track A tails unless the user reprioritizes graph curation.
> **Source:** User decision 2026-07-05: implement Related-entries P2, including backfill between older
> entries and the optional `memory-seed link add` helper.
> **Scope:** Add controlled mutation helpers for explicit `related_entries` curation while preserving
> append-only session-entry semantics.
> **Non-goals:** No silent rewriting of historical entry prose. No automatic graph generation. No
> Memory Trace write/curation UI. No ranking changes. No sidecar graph store unless the in-entry approach
> proves insufficient during implementation.
> **Boundary with the evolution-edges seeding pass (reconciled 2026-07-10):** the two mechanisms
> are complementary and must not blur. The lineage seeding pass in
> [`evolution-edges-plan.md`](../5_Completed/evolution-edges-plan.md) writes **new** clarification entries that
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
  [`completed/related-entries-generation-plan.md`](../5_Completed/related-entries-generation-plan.md).
- Current 3.0 coordination:
  [`3.0-plan.md`](../5_Completed/3.0-plan.md), [`0_NEXT_STEPS.md`](0_NEXT_STEPS.md).
