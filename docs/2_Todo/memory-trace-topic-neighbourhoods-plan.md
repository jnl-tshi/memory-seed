---
memory-system-version: 2.16
tags:
  - memory-seed
  - proposal
  - memory-trace
  - memory-trail
  - topics
  - graph
---

# Memory Trace Topic Neighbourhoods Plan

Status: ACTIVE - accepted for implementation; implementation not started.
Priority: P3 after release-safety, encoding hardening, and Memory Trace package release ordering. It
should run before AI timeline summarisation because topic filters become part of the evidence-pack
contract.
Source: Promoted from `docs/2_Todo/completed/memory-trail-graph-and-topic-neighbourhoods.md` and
folded with `docs/2_Todo/completed/graph recommendations.md` on 2026-07-08. Clarified by user
decision on 2026-07-08:
indexed topics should become the normal session-entry model, with 1-3 topics per entry and a unique
topic index per project.
Scope: Define and implement controlled topic neighbourhoods as a core Memory Seed session-entry
contract and Memory Trace graph/trail view.
Non-goals: No graph database. No committed authoritative graph index. No full mesh between entries
that share a topic. No automatic historical backfill. No Memory Trace write UI.
Dependencies: `docs/3_Spec/graph-edge-contract.md`, `docs/2_Todo/memory-trace-distribution-plan.md`,
`docs/2_Todo/related-entries-p2-mutation-plan.md`, `docs/2_Todo/session-decision-diagrams-plan.md`,
and the live/seed `session_logging.md` skill.
Acceptance criteria: See "Acceptance Criteria" below.

## Assessment

The proposal is accepted as the desired direction, but the code path has not been implemented yet. It
changes the authored session metadata surface by introducing controlled `topics:` fields and a
project topic index. That crosses from derived UI behavior into Memory Seed's durable session
contract, so implementation must touch seed/init, session logging guidance, parsing, retrieval,
validation, MCP, and Memory Trace deliberately.

The useful core is:

```text
related_entries = explicit memory trail
topics = deterministic neighbourhood membership
branch = workstream axis
supersedes = decision replacement
commits = implementation evidence
chunks = retrieval/highlighting units
Memory Trace graph = derived read-only view
```

That is aligned with the current architecture: Markdown stays authoritative, graph state is derived,
and Memory Trace remains read-only.

## Current Implementation Truth

Memory Trace already has "topic" facets and graph edges, but they are not authored YAML topics.
Today they are display topics derived from:

```python
sorted(set(chunk.tags) | set(chunk.contexts))
```

So the proposed `topics:` field is not just documentation. It would create a new controlled topic
surface that should either supersede or augment the current tag/context-derived display topics.

## Recommended Shape

Add an indexed `topics:` list to meaningful session entries. The normal target is 1-3 topics per
entry:

```yaml
entry_id: mse_0123456789abcdef
user_initials: JNL
agent_type: codex
agent_name: null
project_path: .
subproject_path: null
branch: main
topics:
  - memory-trace
  - graph-trails
related_entries:
  - mse_abcdef0123456789
supersedes: []
commits: []
```

Add a controlled topic index as core project state:

```text
.memory-seed/topics.yaml
```

Recommended index fields:

```yaml
schema_version: 1
topics:
  - slug: memory-trace
    label: Memory Trace
    description: Local read-only UI, graph view, timeline, reader, search, stats, and companion distribution.
    status: active
    aliases: [trace, lense, explorer]
```

## Decisions Resolved

- `topics:` is the new normal session-entry field for meaningful entries, not a Trace-only
  enhancement.
- Each meaningful new entry should carry 1-3 canonical topics.
- `.memory-seed/topics.yaml` is a core per-project index. It should be created as project-local state
  and then evolve uniquely for that project; `update` must not overwrite local topic curation.
- Memory Trace should keep its current tag/context-derived display topics as a fallback when indexed
  topics are absent or old entries predate the new field.
- Historical backfill is out of scope for the first implementation; old entries without `topics`
  remain valid.

## Remaining Design Details

- First implementation should ship CLI validation before MCP topic-management tools. MCP topic tools
  can follow once `topics list/check` semantics are stable.
- Decide whether the starter `topics.yaml` is a minimal generic file or generated from project
  bootstrap context. Either way, it must be deploy-once/project-local, not a version-overwritten
  seed/live twin.
- No core continuity topics need seeding: `evolution-edges-plan.md` D6 (revised 2026-07-10) records
  rename/migration/removal events as a structured `continuity:` entry field (kind/from/to) rather
  than topic vocabulary, so continuity membership is derivable from that field. If Trace later wants
  a "continuity events" chain, derive it as a display axis (like `day`/`agent` chains) - do not add
  `rename`/`migration`/`removal` slugs to `topics.yaml`, or membership would be authored in two
  places.

## Blind Spots To Resolve

- Topic sprawl: agents may invent near-duplicates unless the session logging skill tells them to read
  the topic index and `topics check` catches unknown slugs.
- Contract ambiguity: the graph-edge contract should distinguish current display topics
  (`tags` + `contexts`) from future controlled entry topics.
- Validation ownership: topic vocabulary validation should not overload `links check` unless the
  project deliberately chooses one all-integrity command. A separate `memory-seed topics check` keeps
  the graph/link validator focused.
- Bootstrap scope: adding a new top-level `.memory-seed/topics.yaml` file is a control-plane/data
  contract change and should be explicitly accepted.
- UI density: topic graph edges should be chronological chains, not pairwise edges between all
  same-topic entries.

## Implementation Plan

### Phase 0 - Accepted Contract

- Update `docs/3_Spec/graph-edge-contract.md` to define display topics versus indexed topics and
  mark indexed topics as accepted but unimplemented.
- Update `docs/3_Spec/functionality-audit.md` with the accepted topic contract.

### Phase 1 - Core Topic Index And Session Metadata

- Add `topics:` guidance to live and seed `session_logging.md`: meaningful entries should include
  1-3 canonical topics.
- Add `.memory-seed/topics.yaml` as deploy-once project-local core state during `init`, with `update`
  preserving project curation.
- Keep old entries without topics valid.
- Do not backfill historical entries.

### Phase 2 - Parser And Retrieval

- Add `topics: tuple[str, ...] = ()` to `MemoryChunk`.
- Parse entry YAML `topics:`.
- Expose `topics` in retrieval result dictionaries.
- Add an optional topic filter after the field is available.
- Keep `topics`, Markdown hashtags, and heading contexts distinct.

### Phase 3 - CLI Validation

- Add `memory-seed topics list`.
- Add `memory-seed topics check` for duplicate slugs, malformed slugs, unknown entry topics,
  deprecated topic use, alias collisions, topic-count warnings, and unused indexed topics.
- Optionally add read-only `topics suggest --from <file>` after validation exists.

### Phase 4 - MCP And Memory Trace

- Add MCP topic tools only after CLI validation semantics are stable.
- Make Memory Trace prefer indexed topics when present and fall back to current tag/context display
  topics otherwise.
- Render topic neighbourhoods as chronological chains in graph/trail views.

## Acceptance Criteria

- New meaningful entries include 1-3 controlled `topics:` values without making old entries invalid.
- `.memory-seed/topics.yaml` is created as project-local core state and preserved by `update`.
- Session logging guidance prevents free-form topic invention when an index exists.
- Retrieval exposes indexed topics distinctly from `tags` and `contexts`.
- CLI can list and validate topics.
- Memory Trace can filter by topic and render topic chains without full-mesh edge explosion.
- No authoritative graph database or committed graph cache is introduced.
- Memory Trace remains read-only.
