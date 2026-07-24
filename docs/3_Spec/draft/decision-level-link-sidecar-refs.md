---
title: Decision-level refs in link sidecars
status: draft
spec_binding: draft
parent: ../lifecycle-edge-linking-sidecars.md
---

# Decision-Level Refs in Link Sidecars

Status: **DRAFT - PARTIALLY IMPLEMENTED as of 2026-07-22.** The live contract is
[lifecycle-edge-linking-sidecars.md](../lifecycle-edge-linking-sidecars.md), which this extends.

Landed: steps 0-2 below — the skeleton gate (one real decision edge, verified drawing to its decision row
in the running Trail), the ref grammar and read path, and validation. **Step 3 (source side) landed
2026-07-24**, in a different shape than staged here: a per-item `dN -> ` arrow prefix rather than a
block-level `source_decision:` field — see the Source decisions section. With grammar v2 (same day,
JNL's mandate) decision granularity is no longer optional at write time: both ends of a new
`replaces`/`evolves` must name their decision wherever one is addressable. Step 4 resolved 2026-07-23
(open question 1). Bare entry ids in the existing corpus are unchanged and no sidecar needed migrating.

**Scope.** This amends the **link sidecar** (`.memory-seed/sessions/links/…`) so a lifecycle edge can
terminate on a specific decision rather than a whole entry. It borrows the decision identity ratified in
[adr-lifecycle-sidecar-contract.md](adr-lifecycle-sidecar-contract.md) but does **not** touch that ADR
lifecycle sidecar family (`.memory-seed/decisions/<adr_id>.md`), which stays draft and unbuilt. Two
different sidecar kinds; only the identity scheme is shared.

**Scope extension — entry YAML at write time (JNL's direction, 2026-07-24, IMPLEMENTED).** The `:dN`
target grammar is also valid in a session entry's **own** `replaces:`/`evolves:` lists at authoring
time — the author is the one party who reliably knows which decision an edge targets, and the
judgment-swarm programme measured implementation-evolves-proposal and deferral-completion (both
inherently decision-shaped) as the dominant under-declared patterns. Entry-yaml decision refs get the
same validation as sidecar refs (`dangling-decision-ref`, `intra-entry-decision-ref`,
`decision-ref-postdates`), enforced additionally at write time by `session append` /
`memory_session_append`; they peel into the chunk's `decision_edges` channel and are never folded into
entry-level lists (the no-projection rule holds in both homes); the Trail merges both sources into one
decision-edge stream. `related_entries` stays entry-level everywhere. Source-side narrowing
(`source_decision`) remains the staged next step for both homes.

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
chunk is generated for that shape.

Measured against the live corpus on 2026-07-21 by running the chunk extractor, which counts
addressability directly rather than inferring it from entry shape:

| Decision chunks | Count | Slug-addressable? |
|---|---|---|
| `…#decision` (singular `### Decision`) | 381 | **no** — no ordinal in the anchor |
| `…#decisions/d1-<slug>` | 131 | yes |
| `…#decisions/dN-<slug>`, all N | 309 | yes |

A form that cannot address 381 of the 512 individually-anchored decisions cannot be the canonical one.

Accepting it as an alias is a deliberate exception to "one spelling per identity": the alternative is
rejecting a paste from our own UI. The normalisation is one-way and lossless, and `link audit --apply`
emits canonical form, so the alias does not accumulate.

## Source decisions

*As built 2026-07-24 the source ordinal is **per item**, not per block — a `dN -> ` arrow prefix:*

```yaml
entry_id: mse_cdndmm2p0dmbkbq9
replaces:
  - d2 -> mse_wh33mc61swqx0vkv:d1
evolves:
  - d2 -> mse_x:d1,d4          # comma form: one edge per target ordinal
  - d3 -> mse_y:d1
```

Absent a prefix, the source is the whole entry, exactly as before. **Why per-item rather than the
block-level `source_decision:` field designed below (JNL, 2026-07-24):** the block field forces one
block per source decision, so an entry whose D2 and D3 each evolve something needs two blocks with the
same `entry_id` — and in the entry's OWN yaml, which is where the grammar now primarily lives, there
is only ever one block, making the field unable to express the common case at all. The arrow rides on
the item that already carries the target ordinal, so both ends of an edge are stated in one line and
all four granularity combinations below fall out without a per-combination rule. The block-key scheme
`(entry_id, source_decision)` is therefore **withdrawn**; link-sidecar blocks keep the identity
`(entry_id, timestamp)` fixed on 2026-07-24 and take the same arrow items.

**Granularity is mandated at write time (JNL, 2026-07-24).** `session append`/`memory_session_append`
refuse a `replaces`/`evolves` ref that leaves an end unnamed: a target with any addressable decision
must carry `:dN` — explicitly `:d1` for a single-decision target — and an entry with 2+ decisions of
its own must prefix every ref with the authoring ordinal. Only a target with no decision section stays
bare. The reason is provenance: the judgment programme measured decision-shaped patterns
(implementation-evolves-proposal, deferral-completion) as the dominant edge shapes, and an unnamed end
is a fact the author knew and did not record — cheap now, unrecoverable later, and it makes downstream
inference cheaper as a byproduct. `links check` cannot enforce it as an error (published entries are
append-only, so a historical bare ref could never be repaired); it warns via
`unaddressed-target-decision` / `unattributed-source-decision` on entries stamped after
`DECISION_GRANULARITY_MANDATE_SINCE` (2026-07-24 09:00) and stays silent on everything before.

**For a single-decision entry, the entry-level and `d1` forms denote the same edge.** They must not both
be written; `links check` reports a duplicate rather than silently creating two edges.

**Staging.** Target-side decisions are the payoff and should ship first; source-side is the smaller half of
the same parser and can follow. Both are specified here so the second half is not designed against a shape
the first half already froze.

### Granularity is per-endpoint, so all four combinations are legal

The two ends are independent. An entry may supersede or evolve a *decision*, and a decision may supersede
or evolve an *entry* — the ends do not have to match:

| Source | Target | Reads as |
|---|---|---|
| entry | entry | today's edge, unchanged |
| entry | `mse_a:d2` | this session's work retires one call from that session |
| `mse_b:d3` | entry | this one call retires that whole session's position |
| `mse_b:d3` | `mse_a:d1` | one call replaced another |

This falls out of the grammar rather than being added to it: `source_decision` is optional on the block
and a decision suffix is optional on each ref, so the four rows are just the presence/absence matrix.
Nothing needs a per-combination rule.

It matters because the mismatched rows are common in practice. A single-decision entry that is wholly
retired by one call in a later multi-decision entry is `decision → entry`; a broad architectural entry
that retires one specific earlier call is `entry → decision`. Forcing both ends to the same granularity
would push each of those back into the overstate-or-understate choice this draft exists to remove.

## Decision edges are a distinct edge set

An edge with a decision at **either** end is not unioned into the entry-level `supersedes` / `evolves`
lists. Only the entry→entry row of the table above lands there, exactly as today.

This is the load-bearing rule. "D2 of B supersedes D1 of A" does not license "B supersedes A" — that is the
overstatement this whole draft exists to avoid, and projecting decision edges up to entry level would
reintroduce it at the read layer. Consumers that do not model decisions therefore **ignore** decision
edges, which is the same rule they already apply to `classify_pending` stubs and `edge_status:
not_applicable`. They see exactly the edge set they see today; nothing regresses and nothing is inflated.

The mixed rows are where this is easiest to get wrong, and both stay out:

- `decision → entry` has a whole entry as its target, so it looks projectable. It is not: "D3 of B
  supersedes A" says one call in B retired A, not that B as a whole replaced it.
- `entry → decision` has a whole entry as its source, so the block looks like an ordinary one. Also not:
  the target is one call, and promoting it would claim the entry retired the whole of A.

`augment_chunks_with_link_sidecars` keeps its current behaviour for entry-level refs and gains a separate
decision-keyed map for the new ones.

## Validation

New `links check` issue kinds:

| Kind | Severity | Fires when |
|---|---|---|
| `malformed-decision-ref` | error | A ref carries any character outside the entry-id grammar and does not parse as a decision ref — including a `#decisions/…` alias that cannot be normalised. **Never scrape the prefix and continue.** |
| `dangling-decision-ref` | error | The entry resolves but the ordinal does not exist in it |
| `duplicate-decision-ref` | error | The same edge is declared both entry-level and as `d1` of a single-decision entry, or twice in any form |
| `intra-entry-decision-ref` | error | A ref's entry id equals the block's `entry_id` — both ends are in the same entry (see below) |
| `dangling-source-decision` | error | *(2026-07-24)* A `dN -> ` arrow names an ordinal the **authoring** entry does not have |
| `unaddressed-target-decision` | warning | *(2026-07-24)* A post-mandate entry leaves a decision-bearing target bare |
| `unattributed-source-decision` | warning | *(2026-07-24)* A post-mandate multi-decision entry omits the arrow prefix |

`dangling-decision-ref` resolution follows the ADR's totality table: `d1` is valid for any entry with a
decision section in any of the three shapes; `d2`+ requires the numbered-heading or inline-bullet shape and
must be within range. An entry with no decision section has no addressable decision at all.

### Forward-only guard

Unchanged in logic. A decision carries no timestamp of its own, so a decision endpoint resolves its
**entry's** heading timestamp from `entry_timestamps` — the same resolution the live spec already pins for
sidecar edges ([lifecycle-edge-linking-sidecars.md:234](../lifecycle-edge-linking-sidecars.md)). "B:d2
supersedes A:d1" is legal iff A predates B.

Because both ends are required to be in different entries (below), the two timestamps are always distinct
entry timestamps and the guard never faces a tie. That is not a happy accident — it is the reason the
prohibition sits in this section rather than beside the other validation kinds.

### Intra-entry edges are forbidden

*Corrected 2026-07-21 (JNL). The first draft of this section allowed `mse_x:d3 evolves mse_x:d1`, breaking
the resulting timestamp tie with the ordinal on the reasoning that "a lower ordinal is older, because
decisions are written in order and the entry is append-only". **That reasoning was wrong** and is
withdrawn — see below.*

**Both endpoints of a lifecycle edge must belong to different entries.** A ref whose entry id equals the
block's `entry_id` is an error (`intra-entry-decision-ref`), whatever the granularity of either end. This
subsumes the self-edge case that entry-level refs already drop.

Two reasons, in order of weight:

1. **The guard has nothing to check.** Decisions carry no timestamp of their own, so both ends of an
   intra-entry edge resolve to one timestamp. There is no temporal order for a forward-only guard to
   verify, and no substitute clock — see the withdrawn reasoning below.
2. **The relationship is thin.** Decisions of one entry are contemporaneous by construction: the entry is
   authored as a single act. If a call genuinely reverses an earlier one from the same sitting, the
   entry's own prose carries that, and a lifecycle edge between two simultaneous decisions asserts a
   sequence that did not happen.

Forbidding is also the reversible direction. If a real case appears, allowing it later is additive;
allowing it now and forbidding it later would break authored data.

#### Why the ordinal is not a clock

The withdrawn reasoning conflated two different guarantees. **Append-only makes ordinals stable** — D2
will never be renumbered, because the entry is never reopened. It does **not** make them chronological.
An entry is written as one act at the end of a unit of work, and D1…DN is the order the author chose to
*present* the decisions — by importance, by dependency, by narrative. Nothing records or requires the
order in which the calls were actually made, and no rule in `session_logging` ties decision numbering to
time.

So "lower ordinal is older" is a convention at best, and an integrity guard cannot rest on a convention:
every author who numbered by importance rather than by time would have a legitimate edge rejected with a
misleading message. This is worth stating rather than quietly deleting, because the ordinal *is* a sound
key (ADR identity) and *is* a sound sort order (Trail rendering) — it is specifically as a **clock** that
it fails, and that distinction is easy to lose.

## Rendering

*Landed 2026-07-22.* The Trail already drew one row per decision, so a decision-terminated edge attaches
to a row that exists. The `supersedes`/`evolves` line now runs to the specific decision rather than to the
entry heading — the difference between "that session replaced this one" and "that call replaced this one."

Two constraints the implementation had to respect, both of which are a silent edge loss if missed:

- Decision edges are computed **after** row expansion (that is the only point at which a decision row id
  exists) and are appended **outside** the graph's `limited_ids` visibility filter, which is keyed on
  entry ids and would otherwise drop every one of them.
- The focus-view neighbourhood expands over a decision edge's two *entries*, purely to decide what is
  displayed. Without that, upgrading a ref from entry-level to `:dN` would make its far end vanish when
  the source is focused. This is membership, not projection: the drawn edge still terminates on the
  decision row, and nothing is added to entry-level `supersedes`/`evolves`.

When the target entry is single-decision it has no separate row, and the edge attaches to its entry row —
which is the same statement, since the entry-level and `d1` forms denote the same edge for that shape.

*Amended 2026-07-24 (source side).* Endpoint resolution is now symmetric: an arrow-prefixed ref leaves
the **authoring decision's** row rather than the entry anchor, resolved by the same rule as the target
(exact `(entry_id, dN)` row when one exists; entry row when the entry was never expanded; dropped
rather than widened when the entry has rows but not that ordinal). One consequence needs stating: an
arrow-prefixed **bare** ref (`d2 -> mse_x`) is decision-level on its source and entry-level on its
target, so it remains a real entry-level edge for `/graph` and lifecycle consumers *and* draws a
decision-row line on the Trail. The Trail suppresses the entry-level twin of any such narrowed edge —
one authored statement draws one line.

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

1. ~~**Does `link audit` gain decision awareness, or stay entry-level?**~~ **RESOLVED 2026-07-23.** Both,
   split along the constitution's core/optional line. The *scoring* stays entry-level and unchanged — its
   evidence (`shared_files`/`shared_topics`/title/embeddings) is entry-keyed and genuinely cannot
   discriminate two decisions of one entry, so it does not try. *Decision awareness lives in the output*:
   `audit_link_gaps` now attaches both ends' decision structure (`entry_body_decisions` → ordinal + name +
   body) to every gap, the CLI surfaces it for multi-decision entries, and `link audit --json` emits each
   candidate as a judgment-ready task (both ends' decision bodies + link/no-link criteria). The
   *narrowing* to `:dN` is deferred to a human — exactly as the edge TYPE already is — or to an external
   judgment agent that reads the decision bodies. That agent (JNL's "swarm of small agents") is an
   **optional layer**, never in the network-free core (Invariant #1): the core does mechanical recall and
   emits the task; the model calls happen outside; the suggested edge is human/guard-approved and stored
   as an ordinary `:dN` edge, so it stays model-independent (Invariant #5). See
   `docs/2_Todo/link-audit-decision-judgment-swarm-proposal.md`. This is the "human narrows" outcome step
   4 predicted, made concrete, with the machine-narrowing path scoped as a separate proposal.
2. **Should ESR count decision edges separately** in coverage metrics, or would that make historical
   coverage look worse by moving the denominator?
3. **Is `related_entries` worth extending to decisions**, or is decision granularity only meaningful for the
   typed lifecycle edges? The live spec already scopes `related` as accepted-but-not-the-focus.

4. **RESOLVED 2026-07-22. The ADR's corpus table has been re-derived from a committed classifier**
   (`scripts/count_decision_shapes.py`) and amended in place: 138 numbered / 383 singular / 1 inline / 42
   no-decision = 564 entries, 521 with an addressable decision, 115 multi-decision. The disagreement had a
   mechanism rather than an arithmetic error — two entry splitters over the same files, one requiring a
   `HH:MM` stamp (564) and one accepting date-only May-2026 headings (589). The 580 below reproduces under
   neither and is superseded. The original question is kept for the record:

   [adr-lifecycle-sidecar-contract.md:75-80](adr-lifecycle-sidecar-contract.md) reports
   125 numbered / 346 singular / 1 inline / 140 no-decision on 2026-07-20, totalling 612 entries. A
   recount on 2026-07-21 finds **580 entries** — fewer than a day later, which append-only makes
   impossible — and 66 no-decision against the ADR's 140. The numbered and singular figures move in the
   plausible direction (125→131, 346→382, and the chunk extractor independently agrees: 131 `d1-` chunks,
   381 singular), so the disagreement is concentrated in the totals and the no-decision bucket: one of
   the two classifiers is counting something the other is not.

   This does not disturb the ADR's *argument* — the singular-to-`d1` convention is what makes the scheme
   total, and that holds at any of these counts. It matters because the table is the evidence anyone will
   cite for coverage, and the first draft of this document cited it verbatim as current fact rather than
   recounting. Both sets of numbers should be re-derived from one agreed classifier before either is used
   to size work.
