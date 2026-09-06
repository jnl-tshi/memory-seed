---
status: active
priority: P0
blocked_by: independent plan review approval
next_action: Re-review this evidence contract before any implementation change is staged.
source: User-requested transitive session-fusion refinement; review verdict REVISE (2026-09-06).
scope: session-fuse inherited-entry admission, merge provenance proof, CLI/MCP parity, documentation, and focused real-Git tests.
non_goals: Do not relabel child entries, invent a historical receipt, accept deleted or renamed branch names without recovery evidence, weaken sidecar checks, or alter the Reflection Ledger workspace.
dependencies: Ratified Constitution append-only/write-surface invariants; adr_branch_session_fuse; adr_merge_branch_primitive.
acceptance_criteria:
  - A verified two- or three-hop aggregate integration carries the exact original child entry and sidecars without relabelling or replaying each child fuse.
  - Every inherited entry has one complete, unique, byte-exact and receipted Git proof; all missing or ambiguous proof shapes refuse before merging.
  - CLI and MCP positive and negative behavior match the core planner exactly.
  - Chronology, append-only, entry/sidecar immutability, and branch authorship remain covered by end-to-end tests.
---

# Transitive session-fusion refinement plan

## Problem and boundary

An aggregate integration branch can already contain an entry fused from a child
branch. Its immutable `branch:` field correctly remains the child workstream,
but the current source-branch equality gate rejects it when the aggregate is
later fused. The narrow refinement permits this only as a proven inheritance
path; a copied YAML block, an arbitrary merge, or a guessed branch relationship
must remain a hard refusal.

## Proposed evidence contract

The existing direct rule remains unchanged: an entry whose `branch:` equals the
source branch is branch-local and proceeds through all existing validation. A
foreign-attributed entry is inherited only if **every** condition below holds.

1. Resolve `branch:` as a current local branch name only (`refs/heads/<name>`),
   not a SHA, tag, remote-tracking ref, or arbitrary revision. The named branch
   must resolve and be an ancestor of the aggregate source tip. A deleted or
   renamed child branch is therefore rejected with recovery guidance: restore
   the exact historical branch ref first, then retry the preview; never edit
   the authored field to make it fit.
2. Compute the evidence window from
   `merge-base(base, source)..source`. No receipt before the current source's
   divergence from the target may explain an entry the target does not contain.
3. Require exactly one source record, one resolved-child record, and one merge
   result record for the entry ID. Each must have byte-identical full entry text
   (including the original child `branch:` value); any duplicate or modified
   record fails closed.
4. In that window find exactly one qualifying **two-parent** merge commit. Its
   first parent contains no record for the ID; its sole non-first parent is
   reachable from the resolved child branch and contains the one exact record;
   the merge result contains that same exact record. Octopus merges are refused,
   rather than selecting an arbitrary non-first parent, and repeated qualifying
   merges are refused as ambiguous.
5. From that qualifying merge through the aggregate source tip, every tree on
   the aggregate's first-parent chain must contain exactly one record for the
   entry ID with byte-identical text. Deletion, absence, mutation, and a later
   byte-identical re-add all break continuity: a receipt proves one admission,
   not a licence to reconstruct the record later.
6. Parse Git's final contiguous trailer block and require exactly one valid
   `Memory-Entry: <entry_id>` trailer for this entry. Missing, malformed,
   duplicated, or non-final-block trailers are not a receipt. The merge
   topology plus this immutable trailer is the durable prior fuse/merge evidence.

The proof is a predicate at the present branch-attribution gate only. It does
not bypass parser validation, changed-path scoping, chronology, existing-entry
immutability, or sidecar-parent checks. It also does not create a recovery mode
for unavailable branch refs: availability is deliberately traded for
provenance certainty.

## Implementation sequence

1. Add a small core proof helper that receives `base`, `source`, and the exact
   parsed source record. It uses only Git ancestry/tree/trailer facts and emits
   a specific refusal reason for branch-resolution, content, topology, receipt,
   or ambiguity failure.
2. Replace the bare foreign-branch rejection with that predicate, preserving
   the direct-equality fast path and every downstream validation unchanged.
3. Keep CLI `session fuse`/`session merge-branch` and MCP
   `memory_session_fuse_preview`/`memory_session_integrate` as adapters over
   the shared planner; do not duplicate proof logic in either surface.
4. Write a session decision through the sanctioned append surface and perform
   an explicit `adr_branch_session_fuse` evolution/review. The review must
   state whether this is a revision or a reviewed no-change and cite the proof
   contract; no ADR source is edited outside that append-only workflow.
5. Update the README and functionality audit with the qualified inherited-entry
   rule and the deleted/renamed-branch recovery guidance.

## Required verification matrix

All cases use real Git repositories and exercise both dry-run and application
where meaningful. The full positive/negative matrix is mandatory for CLI and
MCP parity, not merely a core-unit substitute.

| Case | Required proof or refusal |
|---|---|
| Two-hop child → aggregate → base | Exact entry, diagram/link/topic sidecars, original child `branch:`, byte preservation, chronological final target, and idempotent re-preview. |
| Three-hop child → aggregate A → aggregate B → base | One inherited record can transit successive verified aggregate merges without branch-by-branch replay. |
| Sidecar preservation | Diagram, link, and topic sidecars retain existing parent, timestamp, append-only, and malformed/orphan rejection behavior. |
| Copied or reintroduced record | A copied child block or a record reintroduced after its receipt fails before merge. |
| Direct delete / direct re-add | Deleting the inherited record on the aggregate and re-adding the same bytes in a later aggregate commit fails the first-parent continuity check. |
| Tampered record | Body/YAML/branch mutation fails byte-exact proof and never lands. |
| Common-ancestry false receipt | A valid old receipt outside `merge-base(base, source)..source` cannot authorize the source. |
| Unrelated parent/ref | A parent not descended from the resolved child ref, a SHA/tag/remote ref, and a deleted/renamed child name fail with actionable recovery guidance. |
| Receipt integrity | Missing, malformed, duplicate, or non-final `Memory-Entry` trailers fail. |
| Ambiguity | Multiple qualifying receipts and octopus topology both fail rather than choosing a lineage. |
| Existing protections | Existing-entry edits, non-chronological records, and malformed/orphan diagram/link/topic sidecars remain rejected. |

## Reflection on context sufficiency

The packet context was sufficient after the review tightened it: the ratified
append-only/write-surface invariants, branch-fuse ADR, one-step merge ADR,
source planner, and real-Git fixture style establish a complete local proof
boundary. No Reflection Ledger material is needed or will be modified. The key
lesson is that a child `branch:` scalar is an attribution claim, not evidence;
only a bounded Git ancestry path plus one exact final-trailer receipt makes it
safe to carry forward.
