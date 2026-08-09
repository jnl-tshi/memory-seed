# Chains as artifacts, and the one-link-per-chain rule

Status: proposed (JNL, 2026-08-09)

## The two ideas

### 1. A chain is a thing, not just a path you can walk

A `refines` chain has an identity: it is the life of one decision through its
successive forms. Some chains become ADRs; JNL's observation is that many
significant chains never will, and the significance lives in the CHAIN, not in
whether anyone promoted it. A chain should therefore be addressable as an
artifact - derivable entirely from the edges (Constitution #6: a derived,
rebuildable projection, never a second source of truth):

- **Identity = the chain's ROOT decision** (the one member with no `refines`
  predecessor). Stable under growth: refining the head extends the chain without
  renaming it, which an id keyed to the head would not survive.
- Derived view: root, ordered members, head (current form), length, and which
  ADR (if any) holds a member as its authoritative decision.
- Surfaces: a `links chain <ref>` CLI/MCP view; Trace can render a chain as a
  unit; ESR can report chains-without-ADRs above a length threshold as promotion
  candidates - the deterministic complement of the keyword-based ADR attachment
  sweep.

### 2. Within one chain, an entry links its evolution ONCE - to the head

If decision 5 continues a chain that runs 1 -> 2 -> 3 -> 4, its `refines` edge
attaches to 4, because that is where the chain lives. A simultaneous "evolves 3"
and "evolves 1" from the same entry is backwards: the chain already carries that
history, so restating it as extra lifecycle edges is redundant at best and
head-ambiguity at worst.

The connection to an earlier member, if worth recording, takes one of two forms
(JNL, 2026-08-09):

- **`related`** - annotation, not lineage.
- **`builds-on` at the head** - a FORK: new work departing from the chain into
  its own line. But the fork also springs from the head, because the head IS the
  most recent iteration of that specific idea - forking from decision 3 would be
  building on a form the chain has already superseded. So the rule generalises
  cleanly: **every lifecycle edge into a chain attaches at its head** - `refines`
  takes the (single) successor slot, `builds-on` forks a new line from it, and
  interior members receive only `related`.

This collapses the chain-position candidate split into one sentence: interior
members are `related`-only, heads take everything.

**Cross-chain multi-evolves stays fully legal.** One entry may evolve several
DIFFERENT chains - that is a merge, and merges are how concerns consolidate
(acceptable, per JNL, even when it merges ADRs). The rule is per-chain, not
per-entry.

## Measured: this is the dominant existing malformation

Of 129 entries that evolve 2+ targets, **67 evolve both X and an ancestor of X**
- more than half of all multi-target evolves restate chain history instead of
extending it. This is not a hypothetical smell; it is the main way the current
corpus deviates from chain shape, and it is exactly the redundancy the
2026-07-24 audit already found ("the dominant under-declared shapes are
decision-shaped") seen from the other side.

## Enforcement

- **Write time (`session append` / MCP):** when a decision's `links.evolves`
  names two targets where one is a chain-ancestor of the other, refuse with the
  concrete fix: keep the edge to the nearer member (for `refines`, the HEAD),
  move the rest to `related_entries`. Same one-moment-it-is-unwritten argument
  as the granularity mandate and the refines cap.
- **`links check`:** `redundant-chain-edge` for post-cutoff edges (advisory on
  published history, hard at append - the established two-tier pattern).
- **Candidate generation:** the chain-position-aware split
  (`chain-position-aware-link-candidates-proposal.md`) already prevents a swarm
  from being OFFERED an interior member as a refines target; this rule is the
  write-side guarantee of the same invariant, so the two ship as one concern.

## Dependencies and order

Depends on the decision-keyed walk (ancestry must be decision-exact), which
depends on the backfill landing - the same critical path as
`adr-refines-review-trigger-plan.md`, and this slots in after its step 3:
chain identity and the redundancy guard are both walks over the same typed,
decision-keyed graph.

## Open questions

- Whether the 67 existing redundant edges get a retract-to-related campaign or
  are simply left as pre-cutoff history the advisory names. (Recommendation:
  leave them; the chain walk ignores non-`refines` edges anyway once typed, so
  their cost after the backfill is noise in `evolved_by`, not wrong lineage.)
- Whether a chain merge (one entry refining heads of two chains) unifies chain
  identity or keeps two roots with a shared head. (Recommendation: keep both
  roots; identity survives, and the shared head makes the merge visible.)
