---
priority: "n/a"
status: "rejected 2026-08-26 (JNL) - wrong mechanism for topic discovery, not a DAG/validity problem"
next_action: "none - see closing note. The write-time, per-agent proposal direction JNL named instead is captured in docs/2_Todo/0_NEXT_STEPS.md."
---

# Topic discovery: swarm output as evidence, not as a vocabulary

Status: **PROPOSAL — 2026-07-28.** Raised by JNL after the decision-axis campaign: *"for the
architecture of the system as a whole there needs to be a way to discover topics in a new project: let
each agent in the swarm emit a few candidate concepts with a confidence score, then aggregate. Use the
stats to propose merges and hierarchies, not finalize them. And keep the area and activity split. Areas
will often form a DAG rather than a neat tree. So treat the swarm output as evidence, then curate the
model from that evidence."*

Nothing here is built.

## The problem this names

Every topic campaign in this repo so far has **assigned from a vocabulary that already existed**. That
is the easy half, and it only works because someone had already written `topics.yaml` by hand from 50
entries of accumulated judgement.

A new project has no such file. The shipped starter is
`architecture, bugfix, documentation, release, workflow` — five slugs, four of them activities, so a new
project begins with **no area axis at all**. A Substack folder's first experience of the vocabulary is
being offered "bugfix" and "release".

So the question is not "which slug fits this entry" but **"what are this corpus's areas?"** — and that
is a different question that has never been asked here.

## What the campaigns already taught, and what carries over

Four measured results from this repo bear directly on the design:

1. **The unconstrained question fails.** Asking one worker to pick 1-of-40 across a hierarchy scored
   **68% inter-worker agreement**; the earlier 2-of-23 pilot scored **0.583** and was aborted. The
   constrained question — "this entry is `memory-trace`; which child?" — scored **0.89–0.94**.
   *Discovery is inherently unconstrained*, which is exactly why its output must not be treated as an
   answer.
2. **Separating the axes helps.** Area and activity judged by separate passes beat a combined pass.
   JNL's instruction to keep the split is consistent with the measurement.
3. **Keyword estimates are worthless as counts.** `inspector` was estimated at ~40 and measured **1**;
   `feature-build` was estimated at ~116 and measured **273**. Two misses of more than 2x in opposite
   directions. Any frequency an aggregation reports must come from judgements, never from term
   presence.
4. **Agreement measures reliability, not validity.** Held-out validity against authored tags was **74%**
   and nothing since has moved it. A discovery pipeline that reports only agreement will look far more
   authoritative than it is.

## The model

### 1. Workers emit candidates with confidence, not labels

Each worker sees a handful of entries (the batch size that worked: ~12 entries, ~17 judgement units)
and returns, per decision, a small set of **candidate concepts** rather than one slug:

```yaml
entry_id: mse_...
ordinal: d1
area:
  - {concept: "topic vocabulary", confidence: 0.9, quote: "..."}
  - {concept: "controlled vocabulary schema", confidence: 0.5, quote: "..."}
activity:
  - {concept: "designing a rule", confidence: 0.8, quote: "..."}
```

Three constraints, each earned:

- **Free text, not slugs.** There is no vocabulary yet. Forcing a slug is what makes the question
  unconstrained-and-scored, which is the shape that failed.
- **A grounding quote per candidate**, as `topic_swarm.md` already requires. A candidate that cannot
  quote the decision is dropped rather than guessed.
- **Confidence is the worker's own**, and is treated as ordinal, not probability. It ranks; it does not
  multiply.

### 2. Aggregation produces statistics, not decisions

Pool every candidate across the corpus and compute, per surface form:

| statistic | what it is evidence for |
|---|---|
| frequency | whether the concept is load-bearing at all |
| mean confidence | whether workers were sure when they said it |
| distinct-worker count | whether it survives independent observation |
| co-occurrence with other concepts | candidate merges and candidate parents |
| entry/decision spread over time | whether it is a phase or a standing area |

**None of these is a slug.** The output of this stage is a table a human reads.

### 3. Merges and hierarchy are PROPOSED from the statistics

- **Merge candidates**: concepts with high co-occurrence and near-identical entry sets are probably one
  concept under two names. Propose `A ≡ B`; do not apply it.
- **Hierarchy candidates**: if A's entry set is close to a SUBSET of B's, propose `A ⊂ B`. Containment
  is the evidence for parenthood, and it is directional in a way co-occurrence is not.
- **Floor**: the existing `MIN_CHILD_ENTRIES` rule applies to a proposed generation-2 branch and not
  below it, as settled 2026-07-27.

Everything here lands in a document with counts beside it, which is the same shape as
`memory-trace-children-proposal.md` — a table where each row carries its evidence and its strength, and
a human rules.

### 4. Areas form a DAG, and that is the part worth measuring first

JNL's claim: **areas will often form a DAG rather than a neat tree.** A single parent is a modelling
convenience, and real areas overlap — `schema` is genuinely both a `lifecycle-edges` concept and a
`topic-vocabulary` one.

**`topics.yaml` cannot express this today.** `parent:` is single-valued and `TopicIndex.ancestors()`
walks one chain. So a DAG is a schema change (`schema_version: 3`), and every consumer that assumes one
root would need auditing — `expand_topic_filter`, `axis_of`, community colour keyed on THE root, and the
`propose_topic_children.py` generation arithmetic.

That is a large change — so it was measured against the 2013 existing attributions before proposing it.

**Result: on this corpus, no evidence for a DAG.**

| measure | |
|---|---:|
| area slugs on ≥5 entries | 30 |
| entries whose decisions span 2+ areas | **109** of 686 |
| area pairs where one is ≥40% inside the other | **0** |
| areas with more than one plausible parent | **0** |

Areas co-occur often (109 entries), but no area sits *mostly inside* another. On this evidence a tree is
adequate and `schema_version: 3` is not justified.

**Two caveats, and the second is the serious one.**

*The first measurement was wrong and is worth recording.* I first computed containment over
**decisions**, which cannot work: a decision carries exactly one area by construction, so two areas can
never co-occur on the same one and every pair scores zero. That was a property of the unit, not of the
corpus. The entry is the right unit, and re-running there gave the table above — still zero, but now for
a reason.

*This measures a vocabulary that was hand-curated AS a tree.* `memory-trace > panes > inspector` is a
tree because someone built it that way, so finding tree-shaped evidence in it is partly circular. What
this genuinely rules out is a DAG **hiding in the current model**. It says nothing about a fresh
discovery run over free-text concepts, where JNL's intuition may well hold — nobody has curated those
into a tree first.

**So: keep the single-parent schema, and revisit only when a real discovery run produces candidates.**
That defers the expensive change to the point where there would be evidence for it, rather than
building for a shape this corpus does not currently have.

### 5. Curation stays human, and the split stays

The swarm never writes `topics.yaml`. That is deploy-once governance —
`memory-seed update` never overwrites it — and it is the safety argument that has held all the way
through: `propose_topic_children.py` cannot write it, and neither can this.

Area and activity remain separate throughout: separate worker passes, separate aggregation, separate
proposal tables. They answer different questions and the campaigns measured that separating them helps.

## What this deliberately does not do

- **It does not score itself against an existing vocabulary.** That was the confound that stalled the
  last campaign — the old tags encoded a different question, so agreement with them measured nothing.
  For a NEW project there is nothing to agree with by construction.
- **It does not report a single quality number.** Reliability and validity are different, and only the
  first is cheap. A discovery run should report agreement AND state plainly that validity is unmeasured.
- **It does not finalise anything.** Every output is a proposal with counts.

## Build order

1. ~~Measure the DAG claim.~~ **Done** — see §4. Unsupported on this corpus; the schema stays
   single-parent, which removes the only step that was not additive.
2. **Candidate-emission prompt + schema**, reusing the batch shape that worked (12 entries, one worker,
   both axes, grounding quotes).
3. **Aggregation script** producing the statistics table. Read-only, no writes to `topics.yaml`.
4. **Proposal renderer** — the evidence table a human rules on.

All remaining steps are additive and touch nothing that exists. Revisit multi-parent only if a real
discovery run over free-text concepts produces candidates with two plausible parents — which is the one
condition this measurement could not test.

## Closing note — REJECTED 2026-08-26 (JNL)

Rejected on the mechanism, not on the DAG/validity findings above (those measurements stand and
would carry over to whatever replaces this). JNL: while this shouldn't be done using a swarm,
proposed topics should be available **at write time** so that agents can propose better topics and
grow the tree if needed, as they write — not as a separate batch discovery sweep over the existing
corpus. The proposals can then be reviewed later, perhaps by a swarm if appropriate, but the
discovery moment itself is per-entry and incremental, not a cold-start batch pass.

This is a different shape from what this doc built: candidate emission here is a retrospective
sweep over ~12-entry batches across the whole corpus, aggregated into statistics before any
proposal exists. JNL's direction has an agent proposing a candidate topic in the moment it writes
an entry, with review deferred rather than discovery deferred. Filed as a fresh direction in
`docs/2_Todo/0_NEXT_STEPS.md` rather than reworked here, since it is closer in shape to
[`vocabulary-proposal-mode-proposal.md`](../5_Completed/vocabulary-proposal-mode-proposal.md) (proposals that don't write, reviewed later) than to this
document's batch-evidence model — but it is write-time and per-agent rather than
measurement-triggered and swarm-run, so it is not simply that proposal either.
