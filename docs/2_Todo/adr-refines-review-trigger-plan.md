# ADR review trigger: a `refines` successor on the authoritative head

Status: approved direction (JNL, 2026-08-09) - build doc for a fresh session

## What it is

An ADR's `authoritative_decision` is a decision ref. If that decision has an
agreed `refines` successor, the concern's current form has moved and the ADR has
not - a mechanical fact. ESR reports it the way `needs-diagram-review` already
reports a diagram invalidated by evolution: name the ADR, its head, and the
proposed successor. **Flag-only.** An authored `revision-proposed` +
`revision-accepted` pair remains the only thing that moves a head
(`feedback_machine_edges_never_move_heads`); the ADR swarm adjudicates each flag.

## Measured case for building it (2026-08-09, 109 agreed-refines edges, 57 ADRs)

- **3 ADRs** have a head with a refines successor; **3 more** on a non-head member;
  51 untouched. A review queue, not a firehose - six items get read.
- The first hit verifies independently: `adr_decision_identity` is headed by
  `mse_kdhw53hzp4nh8wwm:d1` (the 2026-07-24 explicit-`:d1` mandate) and the chain
  proposes `mse_h297nf3qghp7ysyk:d1` - the decision that RELAXED that rule. Both
  were read from source this session for unrelated reasons; the ADR genuinely
  points at a superseded form.

## Build order (dependencies are real, do not reorder)

1. **`retracts:` reaches entry-YAML edges.** Today a sidecar's retract set is
   applied only to `sidecars.get(eid)` in `augment_chunks_with_link_sidecars`,
   so an edge authored in entry YAML cannot be retracted at all - 232 of the 807
   backfill edges are entry-YAML. Apply the retract set to the CHUNK's lists too.
   Tests: a sidecar block retracts an entry-YAML edge; a block cannot retract an
   edge keyed to a DIFFERENT entry_id.
2. **Apply the backfill.** Verdicts validated and preserved (`results2/` + run-1
   `results_VALIDATED_KEEP/`, agreement rule in `apply.py`: 110 refines / 697
   builds-on). Gate on the GRAPH assertion (edge set unchanged, typed count as
   planned) - `links check` read OK while 807 edges vanished, twice.
3. **Re-key the lineage walk to decisions.** `refined_by` /
   `refines_lineage_head` are entry-keyed; an ADR head is `mse_x:dN`.
   `decision_edges` already carries both ordinals - key the walk by
   `(entry_id, ordinal)`, defaulting a missing ordinal to `d1` on
   single-decision entries (the 2026-07-24 relaxation makes them the same node).
   This also removes the source-ordinal inference the measurement had to make.
4. **The ESR section.** For each ADR with `authoritative_decision` set: walk
   `refines_lineage_head` from the head; if non-empty, emit
   `ADR <id>: head <ref> has current form <head-of-chain> - propose a revision or
   record reviewed-no-change`. Also list non-head members with successors, marked
   secondary. Follow the chain to its TERMINUS, not one hop.
5. **Gate flip** (separate, after the backfill lands): untyped `evolves` becomes
   a `links check` error with no cutoff - JNL rejected the cutoff.

## Where things are

Scratchpad `HANDOFF.md` has resume + agreement-rule details; `apply.py` is the
writer; all 47 batches validate. Schema/guards/walk merged `13f11d9..7bc7889`.
