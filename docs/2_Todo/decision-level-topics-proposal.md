---
priority: P3
next_action: PROPOSAL — deferred, not scheduled. Decision-level topic keying (topic:dN) is elegant but does not yet earn its complexity; revisit only if a concrete consumer needs per-decision topic precision (e.g. tinting Trail decision rows by topic). The current topic-inference conventions recorded here ARE live and feed the topic-backfill swarm prompt.
---

# Decision-level topics

Status: **PROPOSAL — deferred 2026-07-25 (JNL raised, assessed against corpus data).** Records the
current topic-inference conventions (live) and the decision-level-keying idea (deferred, with its
reasoning) so the decision is not re-litigated from scratch.

## Current conventions (LIVE — this is what the swarm prompt teaches)

Topics are authored (and inferred) entry-level metadata. Two things about *how* they are chosen are
corpus-measured, not imposed, and the topic-backfill swarm prompt is built from them:

**The two axes.** A well-tagged entry names one of each, ~2 topics total (corpus average 2.26):

- **Area / subsystem — WHERE the work is:** memory-trace, memory-seed, graph, retrieval, session-fuse,
  session-layout, session-logging, mcp-tools, hooks, mermaid, windows-encoding, control-plane,
  process-management.
- **Activity / kind of work — WHAT was done:** ui-design, bugfix, documentation, proposal-lifecycle,
  release, git-workflow, agent-collaboration, tooling-evaluation, security, performance.

**Cross-cutting concerns are add-ons, not a third axis.** `windows-encoding`, `performance`, `security`
are quality attributes that span any (area, activity) pair rather than naming a subsystem or a
work-verb. They total ~11 uses across the whole corpus — far too thin to justify a third mandatory
pick. The swarm treats them as *rare add-ons*: reach for one only when a quality concern is genuinely
the theme (`performance` fix in the `graph` layer), never as a routine third slug. **A third
mandatory axis was assessed and rejected** — it has no home in the vocabulary beyond these three
low-use slugs and would push topics/entry past the measured 2.26 norm.

**The count cap is 4** (`MAX_INFERRED_TOPICS`), set to the corpus authored *maximum*, not the typical
1-3, so an inferred topic is never held to a stricter standard than the author. Multi-decision entries
sit higher in that range (avg 2.76 topics for 2-decision vs 2.10 for single-decision — measured), which
is why the cap is not pinned at 3. It still exists: a label applied to everything distinguishes nothing.

## The idea: key each topic to its decision (`topic:dN`)

Instead of an entry-level `topics:` list, attach each topic to the decision it describes, mirroring the
`:dN` lifecycle-ref grammar shipped 2026-07-24:

```yaml
topics:
  - ui-design:d1
  - bugfix:d2
  - graph:d2
```

This would *unify* two of JNL's three questions: a multi-decision entry accrues more topics naturally
(one small set per decision) with no special cap, and per-decision precision falls out for free.

## Assessment — why it is deferred, not built

1. **Topics are a fuzzy, associative signal by design.** The purpose of a topic is coarse grouping
   ("show me everything about the graph"). A lifecycle edge is a *precise claim* (X evolves Y); "this
   decision is *about* ui-design" is soft aboutness. Decision-level precision fights what topics are
   *for*. The `:dN` grammar earns its keep on lifecycle edges precisely because those are exact; the
   same machinery on a fuzzy signal is precision without a payoff.
2. **The swarm already struggles with the coarse version** (28% exact-set agreement on the blind
   pilot, though calibration and recall are good). Per-decision *attribution* — deciding which of four
   decisions each topic belongs to — is a markedly harder inference, and it would make the 206-entry
   backfill materially less reliable.
3. **Full-stack cost.** It touches the `topics:` grammar, the parser, `MemoryChunk.topics`' shape, and
   every consumer (facets, `topics check`, search filter, Trail).
4. **Marginal payoff.** The concrete uses (retrieval precision, tinting Trail decision rows by topic)
   are thin — a reader opens the whole entry anyway, and topic filtering already returns the entry.

## When to revisit

The `:dN` precedent makes this **cheap to add later**. Revisit when a *specific* consumer needs
per-decision topic precision — the clearest trigger is a Trail feature that colours or filters
individual decision rows by topic. Until then, entry-level topics + the two-axis convention + the
cap-4 rule are the right resolution, and multi-decision entries are served by the raised cap alone.

## References

- `docs/3_Spec/draft/decision-level-link-sidecar-refs.md` — the `:dN` grammar this would mirror.
- `docs/3_Spec/lifecycle-edge-linking-sidecars.md` — topic sidecar family lives beside the link one.
- `memory_seed/core.py` `MAX_INFERRED_TOPICS`, the topic-sidecar validation.
- `docs/2_Todo/link-audit-decision-judgment-swarm-proposal.md` — the sibling swarm (lifecycle edges),
  same mechanical-recall → haiku-judgment → human-validation shape the topic backfill uses.
