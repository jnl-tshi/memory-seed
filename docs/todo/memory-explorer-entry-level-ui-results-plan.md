---
memory-system-version: 2.15
tags:
  - memory-seed
  - proposal
  - memory-explorer
  - ui
  - retrieval
---

# Memory Explorer Entry-Level UI Results Plan

> **Status:** ACTIVE - scoped UI proposal, created 2026-07-05. **Core contract implemented
> 2026-07-05 (unreleased):** the shared retrieval service now owns the rollup
> (`EntryRollup`/`rollup_entry_matches`/`rollup_entry_results` with `best_match_chunk_id`,
> `matched_sections`, `score_source`), Lense entry-granularity search collapses section matches into
> one selectable entry-level result, section/all granularities and MCP stay unchanged, and UI copy
> uses entry/"session entry" with "Matched section" chips. Remaining for the Explorer/Trail UI pass:
> reader-view scroll-to/highlight of the best-matching subsection and section anchors.
> **Priority:** P2 companion to
> [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md). It should
> shape the Explorer/Memory Trail retrieval-service contract before the UI is extracted into the
> companion package.
> **Source:** User decision 2026-07-05: current Memory Lense can show individual session-entry
> subsections as selectable frontend chunks, but that granularity is unhelpful for users. A highly
> relevant subsection should be highlighted inside its parent entry rather than acting as its own
> selectable result.
> **Related source learnings:** [`designing-user-interfaces-source-learnings.md`](../inbox/designing-user-interfaces-source-learnings.md)
> recommends system-level UI coherence, perception/hierarchy, clear navigation, component
> consistency, microcopy, and UI audits. This proposal applies those principles to the Memory Trail
> search and reader model.

## Decision

Memory Explorer should present **session entries** as the primary selectable UI object. Section-level
matches may influence ranking and highlighting, but they should not appear as independent selectable
frontend records.

In practical terms:

- Search results list entries, not entry subsections.
- Compact UI copy should say "entry"; use "session entry" only where disambiguation helps.
- Reader/detail views open the parent entry.
- Highly relevant subsections are highlighted, scrolled into view, or summarized inside that parent
  entry.
- The UI may show matched section headings as context chips or anchors, but selecting them keeps the
  user inside the entry reader.
- `chunk_id` remains a valid retrieval concept, but the Explorer frontend should treat `entry_id` as
  the canonical deep-link target for user navigation.

## Rationale

Subsection chunks are useful for retrieval precision, but poor as primary user-facing objects:

- They fragment one decision record into multiple apparent records.
- They make navigation feel more technical than conceptual.
- They weaken the user's sense of chronology and authorship.
- They create duplicate-looking search results when several subsections of the same entry match.
- They hide the surrounding decision, rationale, alternatives, files, and tests that make a session
  entry useful.

The UI-design source learnings reinforce the same direction:

- **Good UI is a system:** results, reader, graph, and timeline should share one primary object.
- **Perception and hierarchy matter:** users should see the important entry first, then the matched
  subsection as emphasis inside it.
- **Navigation should stay clear:** avoid two competing selectable object types unless both are
  genuinely useful.
- **Microcopy and component consistency matter:** use labels like "Matched section" or "Best match"
  consistently, not raw chunk terminology.

## Proposed Behavior

### Search Results

Return or render one visible result per `entry_id`.

Each result should include:

- entry title and timestamp;
- source path and line range;
- author/agent metadata where available;
- highest-matching section heading, when applicable;
- highlighted excerpt(s) from the best subsection match;
- score/explainability fields rolled up from the strongest match.

If multiple subsections in the same entry match, group them under that entry as secondary context.

### Reader View

Opening a result should show the full entry. If the best match came from a subsection:

- scroll to that subsection;
- highlight the matched text or section block;
- keep the full entry context visible and easy to navigate.

The reader may expose internal anchors such as `#reason` or `#tests`, but those anchors are not
separate cards, graph nodes, or timeline records.

### Graph and Timeline

Graph and timeline views should use entries as primary nodes/events. Section-level matches can
annotate an entry node/event, but should not create extra nodes by default.

### API / Retrieval Service

The Explorer retrieval service can still use section chunks internally. The user-facing result
contract should collapse them into entry-level records with fields such as:

```yaml
entry_id: "<canonical selectable id>"
best_match_chunk_id: "<entry or section chunk that produced the strongest match>"
matched_sections:
  - heading_path: ["Decision"]
    chunk_id: "<section chunk id>"
    excerpt: "<short highlighted excerpt>"
score:
  source: "entry|section-rollup"
```

Names are illustrative; final names should align with the Phase-1 public retrieval service.

## Non-Goals

- Do not remove section extraction from core retrieval.
- Do not change MCP behavior solely for Explorer UI preferences.
- Do not prevent advanced/debug views from exposing raw chunk IDs when explicitly requested.
- Do not introduce write/curation behavior.
- Do not redesign Memory Lense broadly; this is a focused object-model and navigation proposal for
  Memory Explorer.

## Dependencies

- [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md), Phase 1:
  public retrieval service contract.
- [`../graph-edge-contract.md`](../graph-edge-contract.md): graph consumers should not fork edge
  parsing or metric meanings.
- [`../inbox/designing-user-interfaces-source-learnings.md`](../inbox/designing-user-interfaces-source-learnings.md):
  UI principles for hierarchy, navigation clarity, component consistency, microcopy, and audit.

## Acceptance Criteria

- Explorer search UI displays one selectable result per entry, even when section chunks drive the
  best score.
- A matched subsection is visible as highlight/context inside the parent entry result and reader.
- Explorer graph and timeline default to entry-level nodes/events.
- API/service tests prove multiple matching section chunks from the same entry collapse into one
  visible Explorer result.
- MCP `granularity="section"` remains available and unchanged for callers that explicitly need it.
- UI copy avoids exposing raw implementation language such as "section chunk" in normal user flows.
- UI copy uses "entry" in compact controls/results and "session entry" where the longer phrase helps
  clarify that the object is a session-log record.
