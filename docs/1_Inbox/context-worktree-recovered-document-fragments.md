---
status: inbox
priority: P1
source: recovered from the uncommitted codex/fix/context-mode-routing worktree on 2026-09-14
scope: design-discovery decision harvesting and authored-topic validation
non_goals:
  - activating behavior whose supporting implementation has not landed
  - replacing the Decision Curator orchestration proposal
  - treating recovered draft text as governing authority
next_action: assess each fragment with its supporting code before incorporating it into a live skill or specification
---

# Recovered Context Worktree Document Fragments

## Status

Non-governing preservation copy. These fragments were unique to an uncommitted worktree whose Context
Mode routing fix had already landed independently. They are retained here because copying their original
files wholesale would overwrite newer control-plane content, while applying them directly would describe
behavior whose supporting implementation has not landed on `main`.

## Design Discovery: Decision-Harvest Curation Gate

Original source: `.memory-seed/skills/design_discovery.md` in the dirty
`codex/fix/context-mode-routing` worktree.

When discovery settles one or more durable choices, complete this gate before handing the result to
an implementation plan or direct implementation. A design document or Task Packet is not a substitute
for the durable decision record.

1. **Decision-harvest draft.** Identify every accepted, durable choice before the handoff. Keep
   questions, tentative options, and rejected alternatives out unless an alternative's trade-off would
   prevent future re-derivation. For each candidate, state D/R/A, whether it came directly from the
   user or was an agent conclusion, proposed area/activity topics, and any credible lifecycle or ADR
   relationship.
2. **Independent curation review.** Dispatch a bounded, read-only curation agent over that draft. It
   returns a per-decision receipt: durable or not; origin; topics; lifecycle disposition or no-edge
   evidence; ADR disposition; and diagram applicability. It uses only the minimal authority and history
   needed, and never reopens or rewrites prior entries, session sidecars, or ADRs.
3. **Guarded record.** The orchestrator resolves the review, then appends accepted decisions through
   `session_logging.md` with the decision-level topics and, where supported, decision-origin metadata.
   It uses the normal link-suggestion/audit path for credible lifecycle candidates. It may create inert
   `classify_pending` link stubs, but live `replaces`, `evolves`, and `related_entries` sidecar edges
   still require the human classification gate in `end_of_turn.md`.
4. **ADR disposition.** The curator reports one of: no ADR needed, existing ADR reviewed, or candidate
   requiring an ADR recommendation. The orchestrator supplies the evidence and recommendation, but
   never creates, promotes, revises, attaches, or advances an ADR without the approval gate in
   `adr_sweep.md`.
5. **Diagrams.** For every positive diagram trigger in `session_logging.md`, the orchestrator creates
   the required Mermaid sidecar using `compact_mermaid_diagrams.md`. An ADR decision normally has a
   diagram; a no-diagram conclusion must state why prose is sufficient.
6. **Receipt and validation.** Before handoff, return the entry IDs, topical/link/ADR/diagram
   dispositions, unresolved items, and the smallest relevant structural checks, including
   `memory-seed links check` and `memory-seed topics check` when their surfaces changed.

If discovery settles no durable choice, record that outcome and skip dispatch. This gate is a
verification-and-curation step, not permission to infer user intent or bypass human authority over
live lifecycle edges and ADRs.

## Decision-Level Topic Sidecars: Authored Topic Ceiling

Original source: `docs/3_Spec/draft/decision-level-topic-sidecars.md` in the same dirty worktree.

> **`TOPIC_COUNT_TARGET = 4` vs `MAX_INFERRED_TOPICS = 4` share a ceiling but govern different
> populations.** `chunk.topics` is **authored** membership (the field's own contract says “1–4 slugs”),
> while `MAX_INFERRED_TOPICS` caps what a *sidecar* may attribute. The 19 formerly flagged entries all
> carry four **authored** topics. Nothing to reconcile; the per-decision cap governs sidecars and
> `TOPIC_COUNT_TARGET` stays on authored topics only—applying it to the rolled-up union would manufacture
> warnings on exactly the multi-decision entries the grammar exists to serve.

The active code and specification on `main` still use an authored-topic target of three. This fragment
must therefore remain evidence until the associated implementation, tests, and migration consequences
are reviewed together.
