---
title: Decision-level topic sidecars
status: draft
spec_binding: draft
parent: ../../2_Todo/decision-level-topics-proposal.md
---

# Decision-Level Topic Sidecars

Status: **DRAFT — GRAMMAR AND VALIDATION IMPLEMENTED 2026-07-25; read side, consumers, and backfill
still unbuilt.** Zero sidecars have been written. This draft extends the topic-sidecar family to
decision granularity **before** any backfill runs, so the corpus is never written twice. Direction
set by JNL 2026-07-25: build decision-level from the start; scan the full corpus, not only the
topicless tail.

What landed in `memory_seed/core.py`: `<slug>:dN` parsing (`_parse_topic_slug`), ordinal-existence
validation against `entry_decision_ordinals` (`dangling-topic-decision`), a malformed-suffix error
(`malformed-topic-ref`), the per-decision cap `MAX_TOPICS_PER_DECISION = 3` with the entry union
uncapped, `(entry_id, heading timestamp)` block identity so a later block is a legal re-attribution,
and the redundancy rule inverted so a decision-keyed slug never reports as restating the author.
Bare slugs behave exactly as before. Six regression tests in `tests/test_links_check.py`; the live
corpus still reports `Session memory integrity OK`.

## Why decision-level, before any write

The entry-level family works and could be backfilled today. Three measurements argue for extending
the grammar first (all re-measured 2026-07-25 against the live corpus):

**Unit correction (2026-07-26).** The figures below were first recorded using
`entry_body_decision_count()`, which counts `- D:` **bullets**. That is the wrong unit for a `:dN`
backfill: the addressable ordinals a ref may target come from `entry_body_decisions()`, and the two
disagree on 10 entries (906 bullets vs **888** addressable at the same snapshot). An old-style entry
with one `### Decision` heading and inline `- D1:`/`- D2:` bullets has exactly **one** addressable
ordinal, so enumerating by bullet would emit `slug:d2` and hard-error as `dangling-topic-decision`.
The corpus also grew. Re-measure before acting on any figure here.

| Measure | Value (2026-07-26) |
|---|---|
| Entries carrying an `entry_id` | 635 |
| **Addressable decisions corpus-wide** | **888** |
| Decisions inside already-topiced entries | 648 |
| Entries with **zero** decisions | 34 |
| Judgment units (decisions + zero-decision entries) | **922** |

The backfill is a swarm judgment per unit. At entry level that is the topicless tail alone; at
decision level it is ~922 units across the WHOLE corpus, because an entry that already carries
authored entry-level topics still has no per-decision attribution — 648 of the 888 decisions sit
inside already-topiced entries. Running entry-level first would not reduce that; it would add
judgments the decision pass then re-derives. The single-decision majority makes the *re-judgment*
cheap, but the write is what costs: see Precedence below.

## Grammar

A topic slug may carry a decision ordinal, mirroring the lifecycle-ref grammar v2 shipped 2026-07-24:

```yaml
entry_id: mse_...
topics:
  - graph:d1
  - ui-design:d1
  - bugfix:d2
```

- **`<slug>:dN`** attributes the topic to decision *N* of the entry.
- **`<slug>`** bare remains permanently legal — not a migration stage. **33 entries have zero
  decisions** and can never carry a decision-keyed topic; a note or observation entry is still about
  something. A file may mix both forms.
- `dN` must resolve against the entry's real decision count (`entry_body_decision_count`), reusing
  the ordinal-existence validation grammar v2 already performs for link refs. A ref to a
  non-existent ordinal is an error, not a warning.
- The slug half resolves against `topics.yaml` exactly as today: unknown slug is an error,
  non-canonical alias warns.

### "Authored" here means write-time, not human-written

*Added 2026-07-26, aligning with
[write-time-sidecar-consolidation-proposal.md](../../2_Todo/write-time-sidecar-consolidation-proposal.md).*

Every use of **authored** below contrasts a slug declared when the entry was written against one a later
sweep inferred from finished prose. It does **not** mean a person typed it. In this repository the author is
an LLM — all 1,023 entry-YAML slugs were chosen by an agent, with `user_initials` recording who the session
was *for*. The distinction the term is carrying is **first-hand versus reconstructed**: a write-time agent had
just done the work, a sweep has only the record of it.

That is why the accepted consolidation proposal makes provenance a declared `source: write-time | derived`
field on the block rather than something inferred from which file a slug sits in. Once topics move into the
sidecar, "authored" stops being readable from the path and has to be stated.

## Roll-up — decision topics DO project to entry level

**This deliberately inverts the link-sidecar precedent.** Grammar v2 holds that decision edges are a
distinct set never projected up, because projecting `A:d1 -> B:d2` up to `A -> B` would assert an
entry-level relationship nobody judged. That reasoning does not transfer to topics: rolling
`graph:d1` up to "this entry is partly about graph" loses no truth and invents no claim.

It is also load-bearing. Every existing consumer is entry-level — `check_topics` filters
`extract_memory_chunks(...)` on `if chunk.topics` and reads authored entry topics only, and facet
counts, the search filter, and `esr` do the same. Without roll-up, an entry whose decisions are fully
topic-tagged still reports as topicless everywhere that matters, and the backfill buys nothing.

The corpus already behaves this way at write time: authored topics average 2.76 per entry on 2-decision
entries versus 2.10 on single-decision ones — write-time authors rolling per-decision themes up into one
list.

Roll-up is a **read-time derivation** (Invariant #6): the sidecar stores decision-keyed slugs, the
reader exposes both channels — the per-decision attribution and the deduplicated entry-level union.
Nothing stores the union.

## Precedence — append-only, most recent wins

Set by JNL 2026-07-25. Topic sidecars stay append-only, and **the most recent block for an entry
wins**; older blocks for the same entry are history, not competing truth. This is the topic-family
instance of the general rule in
[sidecar-supersession-model.md](sidecar-supersession-model.md), which states it once for all three
families — topics and diagrams supersede per *entry*, links per *edge*.

This is the right resolution because a topic assignment is a *state*, not an independent assertion.
Link edges each stand alone, so downgrading one needs the explicit append-only `retracts:` mechanism
built 2026-07-25. A topic list is replaced wholesale by a better one, so replay-newest-wins expresses
the correction with no new syntax — the same shape the draft ADR contract uses, where
`current_status` is the result of replaying the transition chain rather than a second authored field.

Consequences:

- The current **`duplicate-topic-block`** error (one block per entry per file) must become legal:
  re-attribution is exactly what a second block expresses.
- Blocks need a **total order**: file date, then block timestamp, then position within the file. Two
  blocks for one entry at the same timestamp in the same file remain an error — that is a
  transcription defect, not a correction.
- A superseded block is never edited or removed (Invariant #2); it stays readable as the record of
  what was previously believed.

This also removes the strongest argument against writing anything early — but the judgment count above
still favours getting the grammar right first, since an entry-level pass adds work the decision pass
re-derives rather than replacing any of it.

## Cap and redundancy, restated for decision granularity

- **Cap moves per-decision.** `MAX_INFERRED_TOPICS = 4` is a per-*entry* cap tuned to the corpus
  authored maximum. Per decision the natural unit is the measured ~2 (one area + one activity), so
  the cap becomes **3 per decision**, and the rolled-up entry union is not capped — a 6-decision
  entry legitimately spans more ground than a 1-decision one. This dissolves the cap debate the
  proposal records rather than re-litigating it.
- **`TOPIC_COUNT_TARGET = 3` vs `MAX_INFERRED_TOPICS = 4` is *not* a contradiction** — corrected
  2026-07-25, having been recorded here as one. They govern different populations: `chunk.topics` is
  **authored** membership (the field's own contract says "1-3 slugs"), so `topics check` warning at 4
  is the authored-guidance nudge working as designed, while `MAX_INFERRED_TOPICS` caps what a
  *sidecar* may attribute. The 14 flagged entries all carry four **authored** topics. Nothing to
  reconcile; the per-decision cap governs sidecars and `TOPIC_COUNT_TARGET` must stay on authored
  topics only — applying it to the rolled-up union would manufacture warnings on exactly the
  multi-decision entries the grammar exists to serve.
- **Redundancy becomes enrichment.** The live rule warns when an inferred topic restates one the
  author already wrote. Under decision keying that rule inverts for the 415 already-topiced entries:
  `graph:d1` against an authored entry-level `graph` *adds* the attribution the author never
  recorded. A decision-keyed slug that refines an authored entry-level slug is enrichment and must
  not warn. A decision-keyed slug restating a slug already attributed **to that same decision** is
  the real redundancy.

## Sequencing — grammar now, swarm after the consumer

The proposal's `next_action` forbids building per-decision *inference* first, gating it behind a
decision-level graph. Building the **grammar** is not inference and does not contradict it: the
decision-node graph can still launch inheriting entry-level topics, and the "prove inherited
colouring is too coarse" gate stands.

What the gate does forbid is running the full ~922-unit swarm before a decision-level consumer exists.
Today the graph endpoint does not call `_expand_decision_rows` — `include_decisions` is Trail-only —
so decision-keyed topics would have nowhere to render. Order:

1. Grammar + validation (this draft).
2. Read side: the per-decision channel and the rolled-up union (task #22).
3. Consumer decisions: facet counts, `topics check`, search filter, `esr` (task #23).
4. Swarm pilot on a sample, measured against known-good authored entries, then the full corpus
   (`topic_swarm` skill, which carries the pilot's pass/fail line and tells you to re-measure counts).
