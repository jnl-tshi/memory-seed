---
priority: P3
next_action: "SHIPPED 2026-07-27 (day after JNL raised it) - not a JNL gate any more. scripts/propose_topic_children.py (gather + score) is built, committed, and has run at least twice on memory-trace, producing docs/2_Todo/memory-trace-children-proposal.md. No follow-up action."
---

# Swarm proposal mode: how the vocabulary grows as the project does

Status: **PROPOSAL — 2026-07-26.** Raised by JNL: *"how do we ensure that the swarms can provide new
topic suggestions as the project expands?"*

## The gap

A swarm can **assign** — pick slugs from `topics.yaml` for an entry or decision. It cannot **propose** —
suggest a slug that does not exist yet.

That is not an oversight, it is the validator working: an unknown slug is an `unknown-topic-slug` error
on the sidecar path and `unknown-entry-topic` in `topics check`. **That guard must stay.** Without it
the vocabulary drifts by accident, every typo mints a category, and the controlled vocabulary stops
being controlled.

But it means the one thing that would actually move the concentration is currently unsayable. The
hierarchy work shipped the machinery for fine distinctions; `memory-trace` is still on 44% of entries
because **nobody has created the children**, and the swarm — the mechanism best placed to read 197
entries and notice they fall into four groups — has no channel to say so.

## Two modes, never merged

| | **Assign** (exists) | **Propose** (this proposal) |
|---|---|---|
| Question | which existing slugs fit this decision? | this slug is carrying too much — what children does it want? |
| Input | one entry/decision | every entry under one over-broad slug |
| Output | sidecar blocks | a **proposal document** for review |
| Writes to corpus | yes, validated | **never** |
| Gate | mechanical validator + human batch approval | human approval of a vocabulary change |

Keeping them separate is the whole safety argument. Assignment writes and is bounded by a closed
vocabulary. Proposal cannot write at all, so it can afford to be speculative — and `topics.yaml` is
deploy-once project-local state that `memory-seed update` never overwrites, so a vocabulary change is
governance, not automation.

## The trigger is a measurement, not a hunch

This is what makes depth *earned* rather than invented. The concentration query already exists
(`scripts/` from the concentration review, re-runnable). It answers "which slug is carrying too much of
its scope" — `memory-trace` 44.2%, `graph` 22.8%, everything else healthy. That output **is** the work
queue: a slug over the threshold is a candidate for children, and nothing else is.

Two evidence gates keep proposals honest, and they are different for the two ways a child can arise:

- **Promoted children** (already authored as an alias) — gate is *authored use*: only promote what some
  entry actually wrote. Step 2 applied this and declined to mint `supply-chain` and `profiling`,
  narrower though they are, because nobody had ever written them.
- **Invented children** (new names) — gate is *concentration*: propose only under a parent that
  measures too broad, and only if the child would claim enough entries to matter.

## What a proposal must carry to be judgeable

A name alone is unreviewable. Each candidate child needs:

- **the parent** and its measured share, so the reviewer sees why this is even open
- **candidate slug + description**, in the parent's axis (a child never crosses axes)
- **the entries it would claim**, with a count and a handful of quoted titles
- **the projected split** — what the parent's share becomes if this lands. A child that claims 3 of 197
  entries does not fix a 44% problem and should be visible as such rather than argued about.
- **quote grounding** per claimed entry, the same standard the assignment validator already enforces

And a rejection criterion stated up front, so a proposal can fail cleanly: **a candidate claiming fewer
than some floor of entries is unearned depth**, and a set of candidates that does not materially reduce
the parent's share has not solved the problem it was triggered by.

## Cadence: two different clocks

- **Assignment runs per merge.** JNL's earlier framing: a branch carries 1–5 entries, `link audit`
  already generates candidates, so the sweep judges tens of items and the backlog never rebuilds.
- **Vocabulary proposal runs on the measurement.** Not per merge — a vocabulary that changed every
  merge would be worse than one that never changed. It runs when concentration crosses the threshold,
  which for a healthy project is rarely.

That asymmetry matters as the project expands: entries arrive continuously and get labelled
continuously, while the *shape* of the vocabulary moves only when the corpus proves it must.

## Why the constrained-choice effect makes this worth doing

The aborted pilot asked *pick ~2 slugs from 23* and scored 0.583/0.613. Once children exist the
question becomes *this entry is `memory-trace` — which of its four children?*: a ~5× smaller answer
space, with the parent already known correct because a first-hand author wrote it.

That is not moving a threshold, it is an easier and better-defined task, and it is the honest route by
which the sweep comes back. Proposal mode is what creates the children that make it possible — so this
proposal is a prerequisite for step 7 having anything useful to do, not a parallel nicety.

## Non-goals

- **No automatic vocabulary edits.** Ever. The output is a document.
- **No relaxation of the unknown-slug guard** on any write path.
- **No re-tagging of history.** Invariant #2 stands; a new child applies going forward, and to old
  entries only as a *gap-filling* addition under the `(source rank, then recency)` rule — a child
  alongside a parent is enrichment, never an override.
- **Not a taxonomy generator.** It proposes children for one over-broad parent at a time, because that
  is the only case the measurement can justify.
