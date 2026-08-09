# Chain-position-aware link candidates: refine only at the head

Status: proposed (JNL, 2026-08-09)

## The idea

When `link audit` builds candidates for a new decision A, it currently treats
every older decision as an equally linkable endpoint. But the lifecycle graph
already knows each candidate's POSITION in a chain, and position constrains what
kind of edge is even coherent:

- **A replaced decision is not a valid target at all** (or at minimum is heavily
  demoted): linking new work to a decision that has been retired creates a branch
  from something that no longer stands. Its terminal replacement is the candidate
  that should appear instead.
- **A decision that already has a `refines` successor is not a valid `refines`
  target.** The one-successor cap makes this mechanical: the slot is taken.
  Refinement can only occur at the HEAD of a chain. An interior decision can
  still be a `builds-on` target - later work may genuinely rest on an
  intermediate form - but it cannot be re-refined.
- **Only a chain head is an open `refines` candidate.**

So the candidate list stops being flat and becomes two lists:

1. **`refines`-eligible** - chain heads only (no `refines` successor, not
   replaced). The full verdict space applies: replaces / refines / builds-on /
   related / none.
2. **`builds-on`-only** - interior chain members. The worker's question shrinks
   to: builds-on / related / none. The refines option is not offered because it
   is not available.

## Why this is worth building

**Correctness.** Today nothing stops a swarm (or a write-time author) from
proposing `refines` onto an interior decision; `session append` and
`links check` then refuse it via the cap, but only AFTER the judgement was made
and possibly after other verdicts in the batch were shaped around it. Filtering
at candidate-generation time means the invalid option is never on the table -
the same closed-list philosophy that fixed identifier invention
(`feedback_swarm_closed_candidate_lists`): do not ask a worker to avoid an
answer you could have removed from the menu.

**Compute.** Splitting the payload by eligibility shrinks the verdict space per
candidate. Measured corpus shape: 303 of 862 decisions have at least one
`evolves` successor, and once the backfill lands ~110 carry `refines`. Every
candidate drawn from those ~110 interior positions asks a strictly smaller
question, and the head-only refines list is far shorter than the full corpus.
Two smaller prompts with smaller answer spaces beat one large prompt with a rule
the worker must remember - and same-shaped vocabularies stop sharing a payload,
which is the other standing swarm lesson.

**Freshness for free.** Surfacing the chain HEAD in place of a replaced or
refined candidate means the swarm always judges against the current form -
exactly what `replacing_head` / `evolved_head` were built to expose at read
time, now applied at candidate time.

## Sketch

In `audit_link_gaps` (memory_seed/retrieval.py), after the gated + ungated
selection, annotate each `LinkGapCandidate` from the lineage graph:

```python
chain_position: str = "head"   # "head" | "interior" | "replaced"
refines_taken_by: str | None = None   # the successor occupying the slot
current_form: str | None = None       # head of the candidate's own chain
```

- `replaced`: drop by default (surface `current_form` as a substitute
  candidate); keep retrievability intact everywhere else - this filters a
  CANDIDATE list, it hides nothing from search (Invariant #7 untouched).
- `interior`: keep, but the swarm payload places it in the builds-on-only list
  and the stub renderer says why (`refines taken by <ref>`).
- `head`: full menu.

`link_swarm.md` then documents the two-list payload; the worker prompt for list
2 simply has no refines option. Write-time gets the same courtesy for free: the
`session append` refusal for a taken `refines` slot already exists, but the MCP
envelope error message should name `refines_taken_by` so the author is told
WHICH decision holds the slot.

## Dependencies

- The backfill must land first (chain positions barely exist until the 807 are
  typed) - see `adr-refines-review-trigger-plan.md`, same critical path.
- The decision-keyed walk (step 3 there) makes `chain_position` decision-exact;
  entry-keyed is an acceptable first approximation only for single-decision
  entries.

## Open question

Whether `builds-on` onto a REPLACED decision should ever be allowed (JNL: "at
the very least, definitely not one that has been replaced"). Recommendation:
disallow at candidate time, allow via explicit authored edge - history sometimes
genuinely rested on the retired form, and append-only means recording that fact
late must stay possible.
