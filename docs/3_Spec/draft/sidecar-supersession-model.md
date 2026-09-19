---
title: Sidecar supersession model — append-only precedence across the three families
status: draft
spec_binding: draft
parent: ../lifecycle-edge-linking-sidecars.md
---

# Sidecar Supersession Model

Status: **DRAFT — TOPIC AND DIAGRAM BLOCK IDENTITY IMPLEMENTED 2026-07-25; links already conformed.**
Direction set by JNL 2026-07-25: *append-only with most-recent-wins should be the approach for all
sidecars that extract information — the reference id gets named, and the date of the addition
provides the priority sort.* This draft states that rule once for all three sidecar families, and
names the one place where the unit of supersession differs.

Landed: topic blocks key on `(entry_id, heading timestamp)`; diagram blocks do the same in the fuse
(`core.py`) and the reader resolves them newest-first (`entry_diagram_sidecars`, ordered by heading
timestamp then block index, so the winner does not depend on directory-walk order). Links were
already conformant. Still open: `topics check` and the other entry-level consumers do not yet replay
precedence, because they do not read sidecars at all (tasks #22/#23).

## The rule

> An extraction sidecar is append-only. For any **named reference**, the newest declaration is
> authoritative; file date plus block order supplies the precedence sort. A superseded declaration is
> never edited or deleted — it remains readable as the record of what was previously believed.

This is Invariant #2 realised for derived attribution: corrections are *additions* that win on
recency, never rewrites. It is also what makes an in-place edit unnecessary in every case the three
families currently face.

**"Extraction" is about first-hand versus reconstructed, not human versus machine.** The author of a
write-time declaration in this repository is an agent, exactly as the author of a sweep's block is;
`user_initials` records who the session was *for*, not who typed. What separates the two is that a
write-time agent had just done the work and a sweep is reading finished prose. Once the accepted
[write-time consolidation proposal](../../7_Replaced/write-time-sidecar-consolidation-proposal.md) folds
write-time values into these same sidecars, that difference stops being readable from the file path and
must be carried by the block's declared `source: write-time | derived` field — and this rule's
newest-wins sort will then order first-hand and reconstructed blocks against each other.

**Settled 2026-07-26 by JNL.** A `derived` block never *implicitly* outranks a `write-time` one:
precedence becomes `(source rank, then recency)`, so a sweep cannot win merely by being newer. It may
override a write-time value only through an **explicit `retracts:` naming it, reviewed by a human
before it is written** — possible, but stated and gated, never a side effect of ordering.

Note what that costs this document's own rule that **topics need no retract construct** (they
supersede per entry, wholesale, on recency). That holds *within* a source class. Across classes it
does not: a `derived` topic block wanting to correct a `write-time` one has, today, no legal way to
say so. Extending a retract-shaped mechanism to the topic family is therefore step 1 of the
consolidation build order, not an optional refinement.

### Topic retraction is scoped to CORRECTIONS, and to nothing else

**Settled 2026-07-27 by JNL.** Keep it narrow. A topic retraction says *this topic is wrong* — an
author's slip, or a `derived` block correcting a `write-time` one. That is the whole use case.

It is explicitly **not** the way to reduce a parent's concentration. That temptation is real and it was
acted on: the first `memory-trace` children proposal argued for retracting the parent from 86 entries
that also carried a finer area slug, on the grounds that the parent was redundant there. It is not
redundant — the root names the **subsystem** and the finer slug names the **component**, so both are
true, and a hierarchy exists precisely to hold facts at more than one level.

The mechanism that deflates a parent is **depth**, and it costs nothing: store the most specific slug
and derive the ancestors (`ancestors()` up, `expand_topic_filter` down), so the parent keeps its full
reach while its canonical count falls. Retraction deletes a statement; derivation reorganises one. Only
the second is appropriate for a number that is merely too large.

The practical guard: a retraction should be judgeable as *"was this claim wrong?"*. If the answer is
"no, it was true but I would rather it were more specific", the answer is a child slug, not a retract.

## What "named reference" means per family — the one real asymmetry

The rule is uniform; the **unit** the reference names is not, and getting it backwards silently
destroys data.

| Family | Named reference | A newer block… |
|---|---|---|
| **Topics** | the entry | replaces that entry's whole topic list |
| **Diagrams** | the entry | replaces that entry's whole diagram set |
| **Links** | each individual **edge** | supersedes only the edges it names |

Topics and diagrams are **state-shaped**: the sidecar holds one current answer per entry, and a
better answer replaces it wholesale. Links are **set-shaped**: each edge is an independent
assertion, and the graph-edge contract holds four independent, never-merged kinds. Applying
block-level replacement to links would mean a block declaring two edges erases the three declared
before it — edges the author never intended to touch.

## Links keep `retracts:` — it is this rule's explicit form, not an exception

Two properties make per-edge supersession insufficient on its own for links:

1. **Removal is inexpressible.** Naming a ref under a different kind downgrades it, but no kind means
   "none", so deleting an edge cannot be said by re-declaration alone.
2. **Reclassification is ambiguous.** With four never-merged kinds, a later block naming
   `related_entries: X` where an earlier block said `evolves: X` could mean either *reclassify* or
   *add a second, parallel edge of a different kind*. Implicit last-wins would have to guess.

`retracts:` (shipped 2026-07-25, `link-retraction.md`, Constitution §4 Policy) resolves both: it is
the explicit verb for *"the newest declaration about this reference is absence."* So links satisfy
the same rule as the other two families — they simply carry one extra token because their unit is
finer. The families converge; links are not the exception.

## Diagrams — the append path that is currently missing

Diagram sidecar block identity is `entry_id` **alone**: a second block for the same entry blocks the
fuse (`core.py:4113`, "duplicate diagram sidecar blocks safe fuse"). Link sidecars already key on
`(entry_id, heading timestamp)` so one entry legitimately accrues blocks over time
(`core.py:4115`).

That missing append path is *why* Constitution v1.4 needed a narrow, human-gated exception to repair
unrenderable Mermaid **in place**: with no way to append a corrected diagram, the only route to a
diagram that renders was editing the published one.

**Change:** adopt the link family's `(entry_id, heading timestamp)` block identity for diagrams, with
the newest block authoritative for that entry's diagram set. A repair then becomes an appended block
that supersedes, and the frozen original stays readable as the record of what was authored.

**Resolved 2026-07-26.** This draft deliberately stopped at making the v1.4 exception
non-load-bearing, leaving retirement as a governance question. JNL then ratified **Constitution v1.5**,
which withdraws it: the capability the carve-out bought now exists *inside* Invariant #2 via the append
path, so the exception was unnecessary rather than dormant — and a carve-out that buys nothing is a
standing invitation to edit history. Invariant #2 now applies to diagram sidecars without exception.

## Precedence order

Total order over blocks addressing the same named reference:

1. sidecar **file date** (the `YYYY-MM-DD` the block is filed under),
2. then **block heading timestamp**,
3. then **position within the file**.

Two blocks naming the same reference at the same timestamp in the same file remain an **error** —
that is a transcription defect or a bad merge, not a correction, and guessing between them would be
arbitrary.

Resolution is a **read-time derivation** (Invariant #6): the sidecars store every block, and the
reader replays them in precedence order to produce the current answer. Nothing stores the resolved
result — the same shape the draft ADR contract uses, where `current_status` is replayed rather than
authored as a second state field.

## Consequences for validation

- **Topics:** the `duplicate-topic-block` error (one block per entry per file) becomes legal —
  re-attribution is exactly what a second block expresses. See
  [decision-level-topic-sidecars.md](decision-level-topic-sidecars.md).
- **Diagrams:** the fuse's duplicate-`entry_id` guard narrows to duplicate `(entry_id, timestamp)`,
  matching the link family.
- **Links:** unchanged. `retracts:` and its `malformed-retract` / `dangling-retract` /
  `retract-before-declaration` validations stand as built.
- **All three:** a superseded block is never edited, moved, or removed. The fuse continues to refuse
  merges that modify published blocks.

## Non-goals

- This does not make sidecars mutable, and does not add an `--allow`-style override to `fuse` or
  `session merge-branch`.
- It does not merge the four edge kinds, or change what any kind means.
- It does not apply to primary session entries, which remain append-only with no supersession at the
  block level — an entry is corrected by a *new entry* that points back, never by a later entry
  winning a precedence sort.
