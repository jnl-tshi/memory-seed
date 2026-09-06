# Transitive session-fusion refinement

## Objective

Permit an aggregate integration branch to carry a child branch's already-fused
session entry without changing its original `branch:` attribution or replaying
the child fuse, while preserving the existing default fail-closed behavior.

## Acceptance contract

1. Keep accepting ordinary branch-local entries only when `branch:` equals the
   branch being fused.
2. Admit an inherited entry only when one uniquely identifiable ancestor merge
   commit shows the exact entry first arrived from its declared child branch:
   the child is a non-first merge parent, the child parent contains byte-identical
   entry content, the first parent does not, the merge result contains it, and
   the merge commit has the exact `Memory-Entry` trailer.
3. Reject all other foreign-attributed entries, including copied records,
   altered records, unrelated merge ancestry, duplicate/ambiguous introductions,
   and unreceipted merge introductions.
4. Preserve the existing chronological ordering, append-only/sidecar handling,
   direct-entry immutability checks, and CLI/MCP behavior because both surfaces
   already call the same core planner.

## Implementation steps

1. Add a narrowly scoped Git-proof helper in `memory_seed/core.py`; it scans
   only the aggregate branch's ancestry and returns an inherited-entry proof
   only on the complete, unique evidence chain.
2. Use that helper only at the current branch-attribution gate. All other
   planner checks remain unchanged.
3. Add real-Git nested integration tests for preview and one-step merge,
   followed by copied, tampered, unrelated, ambiguous, and unreceipted negative
   controls. Exercise MCP preview/integrate parity if its adapter needs a
   separate assertion.
4. Run focused fuse, CLI, MCP, and link validation; then record a concise
   workstream reflection on evidence/context sufficiency.

## Reflection

The task packet/context was sufficient: the fuse ADR, Constitution append-only
invariant, prior merge-branch rationale, and the source planner/tests exposed
the exact authorization boundary without needing the separate Reflection Ledger
workspace. The only implementation-specific addition was the strict proof
shape: current declared child ref plus a unique receipted ancestor merge and
byte-identical record. That is intentionally narrower than trying to infer
branch authorship from copied session text. A deleted child ref now fails closed;
this is a deliberate availability trade-off for durable provenance rather than
an undocumented recovery path.
