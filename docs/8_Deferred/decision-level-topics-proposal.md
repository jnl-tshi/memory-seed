---
priority: P3
status: deferred
deferred_reason: "Per mse_pww2f69g5ket96h6 D1 and mse_jz0pwv0ngzzxr484 D2, decision-level topic keying/backfill is not built and waits for a demonstrated decision-level graph consumer; the measured swarm backfill was aborted."
revisit_when: "A decision-level graph consumer is accepted and inherited entry topics prove too coarse for its colouring/filtering needs."
next_action: PROPOSAL — decision-level topic *inference* stays gated behind a DECISION-LEVEL GRAPH (JNL's vision, 2026-07-25): topics are the colouring/clustering layer that graph needs, not standalone precision. Sequence — (1) render the decision-node graph using the substrate that already exists, decisions inheriting their entry's topics; (2) run per-decision inference only if inherited colouring proves too coarse. AMENDED 2026-07-25 (JNL): the *grammar* is built first and is not inference — see `3_Spec/draft/decision-level-topic-sidecars.md`. Rationale: the backfill is 881 decision judgments across all 621 entries whether or not an entry-level pass runs first, so an entry-level backfill would be written twice. Sidecars are append-only with most-recent-block-wins precedence. Current entry-level topic-inference conventions here are LIVE and feed the swarm prompt.
---

# Decision-level topics

Status: **PROPOSAL — 2026-07-25.** Reframed by JNL from "topic precision" to "the enabler of a
decision-level graph." Records the live entry-level conventions, the vision, and the de-risked
sequencing so the decision is not re-litigated from scratch.

## Current conventions (LIVE — this is what the swarm prompt teaches)

Topics are authored (and inferred) entry-level metadata. Two things about *how* they are chosen are
corpus-measured, not imposed, and the topic-backfill swarm prompt is built from them:

**The two axes.** A well-tagged entry names one of each, ~2 topics total (corpus average 2.26):

- **Area / subsystem — WHERE the work is:** memory-trace, graph, retrieval, session-fuse,
  session-layout, session-logging, mcp-tools, hooks, mermaid, windows-encoding, control-plane,
  process-management — plus **`memory-seed`, which is the RESIDUAL area**, not a peer of the others.
  *(Sharpened 2026-07-26.)* Use it only when no narrower area applies, and **never alongside another
  area slug**. Its old description named a concrete surface ("Core package, CLI, MCP, seed runtime")
  *and* a residual ("behavior not captured by narrower topics") in one sentence, which no annotator
  could apply consistently — measured, the corpus split almost exactly in half: of 107 entries using
  it, **53 used it as the only area and 54 alongside a narrower one**, which a true residual can never
  be. Its concrete half also double-named `mcp-tools`' territory (CLI and MCP appear in both
  descriptions).
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

This would *unify* two of JNL's three topic questions: a multi-decision entry accrues more topics
naturally (one small set per decision) with no special cap, and per-decision precision falls out for
free. On its own that reads as thin — but it is not the point. See the next section.

## The motivating vision — a decision-level graph (JNL, 2026-07-25)

The reframe that justifies this: **make the graph's node a DECISION, not an entry.** Each decision
becomes a node, carrying its own subsystem + activity topics, so the relationship map is drawn at the
grain the project actually reasons in (decisions are the unit of memory, not entries). Per-decision
topics stop being standalone precision and become the **colouring / clustering / filtering layer that
a decision-node graph requires** — inheriting one topic set across all N decisions of an entry would
paint them identically and defeat the view.

This also dissolves the entry-level topic-count cap debate entirely: the natural unit becomes ~2
topics *per decision*, so a 6-decision entry carries ~12 topics distributed 2-per-node and no fixed
entry cap is needed. The "4 is too few for a big entry" instinct was right, aimed one level too high.

**The substrate is ~two-thirds built already:**

- `_expand_decision_rows` (service.py) already turns an entry into one node per decision — the Trail
  uses it; the graph endpoint simply does not call it (`include_decisions` is Trail-only today).
- Decision-level `:dN` edges already terminate on decision rows (`_decision_edges_for_rows`), so
  decision→decision links exist.
- Node-count growth is ~40% (≈847 decision nodes vs 596 entries) — manageable.

What is genuinely missing: (1) wiring the graph endpoint + client to render the decision-node set and
its layout; (2) per-decision topics as the colouring layer.

## Sequencing — de-risk by decoupling (the actual plan)

Per-decision *topic inference* is the hard, unreliable part (the swarm manages only 28% exact on the
coarse entry-level version; attributing each topic to the right decision is harder). So do NOT build
it first. Instead:

1. **Render the decision-node graph using what exists**, with each decision **inheriting its entry's
   topics** for colour. No new grammar, no swarm, no authoring — just call `_expand_decision_rows`
   from the graph path and colour by inherited topic. This proves whether a decision-node graph is
   actually more legible than the entry graph. It might be enough on its own.
2. **Only if inherited colouring proves too coarse** — all decisions of an entry the same colour,
   clusters muddy — build per-decision topics as the refinement, against a graph already shown to want
   them. That is the demonstrated need this proposal was waiting for.

This front-loads the cheap validation and defers the expensive/risky swarm work until it is proven
wanted. Entry-level topics + the two-axis convention + the cap-4 rule remain correct for the current
entry-level graph in the meantime.

## References

- `docs/3_Spec/draft/decision-level-link-sidecar-refs.md` — the `:dN` grammar this would mirror.
- `docs/3_Spec/lifecycle-edge-linking-sidecars.md` — topic sidecar family lives beside the link one.
- `memory_seed/core.py` `MAX_INFERRED_TOPICS`, the topic-sidecar validation.
- `docs/7_Replaced/link-audit-decision-judgment-swarm-proposal.md` — the sibling swarm (lifecycle edges),
  same mechanical-recall → haiku-judgment → human-validation shape the topic backfill uses.
