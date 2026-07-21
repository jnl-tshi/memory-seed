---
title: Decision-level refs in link sidecars
status: draft
spec_binding: draft
parent: ../lifecycle-edge-linking-sidecars.md
---

# Decision-Level Refs in Link Sidecars

Status: **DRAFT - NOT IMPLEMENTED.** The live contract is
[lifecycle-edge-linking-sidecars.md](../lifecycle-edge-linking-sidecars.md), which this extends. Nothing
here is built; no existing sidecar is affected until it is.

**Scope.** This amends the **link sidecar** (`.memory-seed/sessions/links/…`) so a lifecycle edge can
terminate on a specific decision rather than a whole entry. It borrows the decision identity ratified in
[adr-lifecycle-sidecar-contract.md](adr-lifecycle-sidecar-contract.md) but does **not** touch that ADR
lifecycle sidecar family (`.memory-seed/decisions/<adr_id>.md`), which stays draft and unbuilt. Two
different sidecar kinds; only the identity scheme is shared.

## Problem

Entries are the unit of authorship, not the unit of decision. A session entry routinely carries three or
four independent calls, and lifecycle relationships between sessions are usually between *one* decision in
each — "the pastel-D1 scheme in B replaced the single-row scheme decided in A" — not between the entries
wholesale.

Today that cannot be said. A ref is a bare entry id, extracted by `findall` over
`_TRAILER_ENTRY_ID_RE` ([core.py:724](../../../memory_seed/core.py)), so every edge is entry-to-entry.
Recording the real relationship forces a choice between two wrong statements: "B supersedes A" (overstates
— most of A stands) or `related_entries` (understates, and renders as faint on-select brackets rather than
a lifecycle line). The lifecycle distinction collapses for the same reason the live spec's Problem section
describes, one level down.

Two things changed that make this worth building now:

1. The decision identity was ratified 2026-07-20: a decision is the pair `(entry_id, dN)`, total across
   all corpus shapes via the singular-`### Decision` → `d1` convention
   ([adr-lifecycle-sidecar-contract.md:62](adr-lifecycle-sidecar-contract.md)).
2. The Trail renders one row per decision as of 2026-07-21, so a decision-terminated edge now has
   somewhere to land. Before that it would have been an edge with no visible endpoint.

### A defect this closes

A ref written today as `mse_abc123#decisions/d2-some-slug` is **silently truncated to `mse_abc123`**. `#`
is outside the regex's character class, so `findall` returns the prefix; the prefix resolves against known
entries, so no `dangling-*` issue fires. `links check` reports nothing. The sidecar looks like it recorded
a decision-level edge and recorded an entry-level one instead — neither honoured nor rejected. Whatever
else this draft does, that path must become an error.

## Ref grammar

A ref is one of two forms. **Bare entry id is unchanged and remains the default**, so no existing sidecar,
stub or `classify_pending` block needs migrating (verified: no decision-shaped ref exists anywhere under
`sessions/links/**` as of 2026-07-21).

```yaml
entry_id: mse_cdndmm2p0dmbkbq9
supersedes:
  - mse_jt2rs0r4k609vx7n          # entry-level - unchanged
evolves:
  - mse_wh33mc61swqx0vkv:d2       # decision-level - "…, specifically its D2"
```

**Canonical form is `<entry_id>:<dN>`.** The colon is safe in a YAML scalar (a mapping needs `: ` or a
trailing colon), and it survives the regex-based block parser the reader actually uses.

### Why not the section slug as the authored form

`mse_abc#decisions/d2-some-slug` is what a reader can copy out of Memory Trace, so it is accepted on read
and normalised to the pair. It is **not** canonical and writers never emit it, for the reason the ADR
already gives — it is an address, not an identity
([adr-lifecycle-sidecar-contract.md:89](adr-lifecycle-sidecar-contract.md)) — plus one that bites harder
here: the slug **cannot express d1 of a singular `### Decision` entry**, because no `#decisions/d1-…`
chunk is generated for that shape. That is 346 of ~610 entries. A form that cannot address the majority
case cannot be the canonical one.

Accepting it as an alias is a deliberate exception to "one spelling per identity": the alternative is
rejecting a paste from our own UI. The normalisation is one-way and lossless, and `link audit --apply`
emits canonical form, so the alias does not accumulate.

## Source decisions

The block key becomes the pair too, via an optional field:

```yaml
entry_id: mse_cdndmm2p0dmbkbq9
source_decision: d2
supersedes:
  - mse_wh33mc61swqx0vkv:d1
```

Absent `source_decision`, the source is the whole entry, exactly as today. Multiple blocks may share an
`entry_id` provided their `source_decision` differs — the block key is `(entry_id, source_decision)`, with
absent treated as a distinct key from any ordinal.

**For a single-decision entry, the entry-level and `d1` forms denote the same edge.** They must not both
be written; `links check` reports a duplicate rather than silently creating two edges.

**Staging.** Target-side decisions are the payoff and should ship first; source-side is the smaller half of
the same parser and can follow. Both are specified here so the second half is not designed against a shape
the first half already froze.

## Decision edges are a distinct edge set

A decision edge is **not** unioned into the entry-level `supersedes` / `evolves` lists.

This is the load-bearing rule. "D2 of B supersedes D1 of A" does not license "B supersedes A" — that is the
overstatement this whole draft exists to avoid, and projecting decision edges up to entry level would
reintroduce it at the read layer. Consumers that do not model decisions therefore **ignore** decision
edges, which is the same rule they already apply to `classify_pending` stubs and `edge_status:
not_applicable`. They see exactly the edge set they see today; nothing regresses and nothing is inflated.

`augment_chunks_with_link_sidecars` keeps its current behaviour for entry-level refs and gains a separate
decision-keyed map for the new ones.

## Validation

New `links check` issue kinds:

| Kind | Severity | Fires when |
|---|---|---|
| `malformed-decision-ref` | error | A ref carries any character outside the entry-id grammar and does not parse as a decision ref — including a `#decisions/…` alias that cannot be normalised. **Never scrape the prefix and continue.** |
| `dangling-decision-ref` | error | The entry resolves but the ordinal does not exist in it |
| `duplicate-decision-ref` | error | The same edge is declared both entry-level and as `d1` of a single-decision entry, or twice in any form |

`dangling-decision-ref` resolution follows the ADR's totality table: `d1` is valid for any entry with a
decision section in any of the three shapes; `d2`+ requires the numbered-heading or inline-bullet shape and
must be within range. An entry with no decision section has no addressable decision at all.

### Forward-only guard

Unchanged in logic. A decision carries no timestamp of its own, so a decision endpoint resolves its
**entry's** heading timestamp from `entry_timestamps` — the same resolution the live spec already pins for
sidecar edges ([lifecycle-edge-linking-sidecars.md:231](../lifecycle-edge-linking-sidecars.md)). "B:d2
supersedes A:d1" is legal iff A predates B.

**Intra-entry edges are legal**, and are the one case the timestamp guard cannot decide: `mse_x:d3 evolves
mse_x:d1` has one timestamp on both ends. The ordinal is the tie-break — within an entry, a lower ordinal
is older, because decisions are written in order and the entry is append-only. So an intra-entry edge is
legal iff the target ordinal is strictly lower than the source's. Without this rule the guard would reject
a genuine "I changed my mind later in this session" edge with a misleading not-strictly-older message.

## Rendering

Out of scope here; noted so the payoff is legible. The Trail already draws one row per decision, so a
decision-terminated edge attaches to a row that exists. The `supersedes`/`evolves` line then runs between
the two specific decisions rather than between two entry headings — which is the difference between "that
session replaced this one" and "that call replaced this one."

## Implementation order

Mirrors the live spec's walking-skeleton discipline: prove the read path renders before building
validation or detection.

0. **Skeleton gate** — hand-author one real decision edge (a 2026-07-21 Trail pair) in a scratch copy, wire
   only the ref parser and the decision-keyed map, and confirm the Trail draws the line between two
   decision rows. If it renders, the rest is mechanical.
1. **Grammar + read** — ref parsing in `core.py` (extraction) and `retrieval.py` (parse), the decision-keyed
   map, alias normalisation.
2. **Validation** — the three issue kinds above, the ordinal tie-break, the totality table.
3. **Source decisions** — `source_decision` on the block, `(entry_id, source_decision)` block keying.
4. **Detection** — whether `link audit` should suggest decision-level candidates at all is an open
   question, not a step. Its evidence is file and topic overlap, both entry-scoped; it has no signal that
   discriminates between decisions of one entry. Probably it keeps emitting entry-level stubs and a human
   narrows them.

## Open questions

1. **Does `link audit` gain decision awareness, or stay entry-level?** (See step 4 — the honest answer may
   be that it cannot, with its current evidence.)
2. **Should ESR count decision edges separately** in coverage metrics, or would that make historical
   coverage look worse by moving the denominator?
3. **Is `related_entries` worth extending to decisions**, or is decision granularity only meaningful for the
   typed lifecycle edges? The live spec already scopes `related` as accepted-but-not-the-focus.
