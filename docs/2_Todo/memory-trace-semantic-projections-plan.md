---
title: Memory Trace semantic projections
status: active
priority: P3
next_action: After B0b and the semantic foundation, validate one Decision projection against the real ADR corpus before considering another projection.
blocked_by:
  - React Trail parity and B0b acceptance
  - memory-seed-semantic-record-and-signal-foundation-plan.md
source: ../7_Replaced/type-specific-trace-projections-exploration.md
---

# Memory Trace Semantic Projections

Status: **ACTIVE, LATER**. The first slice is one user-validated Decision projection, not a family of
type-specific pages.

## Outcome

Make the semantic foundation visibly useful in Trace while retaining one shared selection, reader, graph,
and API model.

Five-question test: **Retrieval** and **Application**.

## First projection - Decisions

- Filter accepted, proposed, rejected, and superseded ADRs from the canonical sidecar reader.
- Show stable ADR identity, current derived status, topics, source decision, transition history, and
  supersession chain.
- Resolve rationale and evidence from the original and decision-update entries.
- Preserve one-click access to the full chronological Trail and unfiltered search corpus.

## Non-goals

- No separate truth store or projection-specific write path.
- No immediate Session/Finding/Planning/Handoff tab set.
- No duplicated reader, graph, search, or selection logic.
- No semantic summary that obscures source references.

## Sequence and acceptance

1. Complete B0b Trail parity and the semantic foundation walking skeleton.
2. Add a renderer-neutral Decision projection fixture to `/api/v1`.
3. Implement the React view with the shared workspace primitives and list alternative.
4. Validate it against real ADRs for source resolution, lifecycle clarity, keyboard access, and scale.
5. Consider a second projection only when user evidence shows a repeated distinct question.

Acceptance requires exact parity between the projected lifecycle and the authored sidecars, direct access to
every source entry, and no loss of ordinary Trail/search visibility.
