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

This does not repeal the v1.4 exception — it makes it **non-load-bearing** going forward, so no
future repair needs to invoke it. Whether to formally retire the exception is a governance question
for JNL, not something this draft decides.

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
