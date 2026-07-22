---
title: ADR lifecycle sidecar contract
status: draft
spec_binding: draft
parent: ../../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md
---

# ADR Lifecycle Sidecar Contract

Status: **DRAFT - NOT IMPLEMENTED**. This contract becomes live only after the walking skeleton and validator
are accepted.

## Authority

One append-only Markdown sidecar is authoritative for an ADR's promotion, stable identity, and lifecycle.
The original and decision-update entries are authoritative for narrative rationale and evidence. Current
project files and live specs remain authoritative for what is implemented now. Registries, databases,
`current_status`, and UI views are derived.

## Shape

Candidate location: `.memory-seed/decisions/<adr_id>.md`, one file per ADR. The directory is introduced only
when this draft is adopted; this documentation pass does not create runtime state.

```markdown
---
schema_version: 1
adr_id: adr_...
source_entry_id: mse_...
source_decision: d1
title: Use SQLite for the local index
topics:
  - storage
created_at: 2026-07-16T14:20:00Z
created_by: jean
---

## Proposed - 2026-07-16T14:20:00Z

update_entry_id: mse_...

## Accepted - 2026-07-16T16:10:00Z

update_entry_id: mse_...
expected_previous_status: proposed
```

Frontmatter identity fields are fixed after creation. Corrections, topic changes, status changes, rejection,
and supersession are appended transition blocks. `current_status` is the result of replaying the single valid
transition chain and is never authored as a second state field.

CLI and MCP writers should use one shared core operation, but the file remains directly readable and editable.
A manual append is authoritative when it satisfies the same schema and validation rules; tooling must not
claim exclusive ownership of repository memory.

## Source decision identity

*Amended 2026-07-20 (JNL). The earlier text proposed, for legacy sources, "a sidecar-owned stable decision
key plus an exact heading path and optional source-text fingerprint". That is withdrawn: three mechanisms
to solve a problem the entry already solves.*

**A decision is identified by the pair `(source_entry_id, source_decision)`** — nothing else. The entry id
already fixes the location, so the ordinal only has to be unique *within* that entry:

```yaml
source_entry_id: mse_77cn2v0rg9na3w0v
source_decision: d1
```

### The ordinal is derived, never authored

No entry is edited to carry decision metadata. The ordinal is read from the structure the DRAFT grammar
already imposes, which covers every shape in the corpus.

*Amended 2026-07-22 (JNL). The counts below replace the hand-derived 2026-07-20 figures (125 / 346 / 1 /
140, totalling 612), which no recount reproduced. They now come from a committed classifier,
`scripts/count_decision_shapes.py` — re-run it rather than re-deriving by hand.*

| Entry shape | Count | Ordinal |
|---|---|---|
| `#### D1 - name`, `#### D2 - name` | 138 | from the heading number |
| singular `### Decision` | 383 | **`d1` by convention** — a single decision is the first decision |
| `### Decisions` with inline `- D1:` bullets | 1 | from the bullet label |
| no decision section | 42 | nothing to identify; not an ADR source |

Total **564 entries**, of which **521 carry at least one addressable decision** and **115 carry two or
more**. Those two figures are what `_entry_decision_ordinals` actually returns, not a sum of the table, so
coverage and validation cannot drift apart: the inline-bullet entry is a shape the table recognises but
yields no ordinal under the current implementation, which is why 138 + 383 = 521 and the inline row adds
nothing to it.

**Why the earlier numbers did not reconcile.** Each prior figure was right about its own population and
neither said which population that was — the corpus has two entry splitters. `_ENTRY_HEADING_RE`, used by
`links check` and by the script above, requires a `HH:MM` stamp; the semantic-cache entry extractor
accepts a date-only `## YYYY-MM-DD - title`. The earliest entries (May 2026, before the timestamp
convention) are date-only, so the extractor counts **589** where the validator counts **564** over
byte-identical files — and 589 is exactly the `entry_count` Memory Trace displays. The 2026-07-21
recount's 580 reproduces under neither splitter, on this branch or on the primary checkout, and is treated
as superseded rather than reconciled.

None of this disturbs the ADR's argument. The singular-to-`d1` convention is what makes the scheme total
rather than partial, and it holds at every one of these counts: without it the 383 single-decision entries
— still the clear majority — would have no addressable decision at all, and they are exactly the entries
most likely to hold one clean architectural call.

### Why not the section slug

Section chunks already exist for many decisions
(`mse_77cn2v0rg9na3w0v#decisions/d1-80-bit-generated-entry-ids`), and that anchor stays: it is how a
reader *retrieves* the decision text, and it is stable because entries are append-only.

But it is an **address, not an identity**, and it must not become the key:

- It is not total. A singular `### Decision` yields `#decision` with no ordinal; inline-bullet decisions
  yield no sub-anchor at all. The pair works for all three shapes.
- It carries the heading text, so the key would encode the title
  (`d1-rollup-lives-in-the-service-entryrollup-lense-adapts-presentation-only`) and change meaning if a
  title were ever reworded.
- It is longer than it needs to be for a value that is compared, indexed, and stored on every transition.

So: **compute on the pair, retrieve by the slug.** They are consistent — the slug's `dN` segment is the
same ordinal — but only one of them is the key.

### What this deletes

- No sidecar-owned decision key. Identity is derived from the source, not invented by the referrer.
- No heading path. The entry id already locates the decision.
- No source-text fingerprint. Append-only already guarantees the source cannot drift, so a fingerprint
  adds a failure mode (formatting changes break it) in exchange for a guarantee already held.

## The sidecar lifts; it does not mirror

The ADR sidecar records **which decisions are architecturally significant, and their lifecycle**. It does
not assign identity, and it is not a projection of every decision.

The corpus holds 710 identifiable decisions (same 2026-07-22 recount; the earlier 471 was the superseded
612-entry table's sum). It should not hold 710 ADRs. Most session decisions are
tactical — a scroll band, a lint message, a test rename — and stay entirely in their entry. An ADR is
created when a decision constrains future work in a topic area, and `topics:` is what groups them, so
"the storage decisions" or "the retrieval decisions" is a query rather than a folder.

This is the division of labour that makes both halves simple: **the entry owns what was decided; the
sidecar owns which of those decisions still governs.**

## Transition rules

- Every transition references exactly one `decision-update` entry.
- The update entry names the ADR, expected previous status, new status, author, timestamp, rationale, and
  evidence references.
- Allowed status transitions are versioned by schema. The initial set is proposed -> accepted/rejected and
  accepted -> superseded. Reconsideration requires an explicit later schema decision.
- Supersession names the replacement ADR; the inverse is computed rather than hand-maintained.
- Competing transitions from the same previous status are a conflict requiring explicit resolution, never a
  last-writer-wins merge.

## Validation

Validation must detect duplicate ADR IDs, broken source selectors, missing update entries, transition/order
errors, competing heads, unknown topics, malformed timestamps, and invalid supersession. It reports repair
guidance but does not silently mutate authored memory.

## Derived readers

Readers may derive current status, transition timelines, topic indexes, supersession chains, and Trace
projections. Every value retains source sidecar and entry references, and a full rebuild from repository
Markdown must produce equivalent output.
