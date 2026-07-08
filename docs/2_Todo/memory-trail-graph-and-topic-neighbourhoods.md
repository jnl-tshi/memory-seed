> Status: SOURCE RESOLVED 2026-07-08. Canonical source archive:
> `docs/2_Todo/completed/memory-trail-graph-and-topic-neighbourhoods.md`. This todo-path copy remains
> only because OneDrive denied removal of the reparse-point file. Canonical active plan:
> `docs/2_Todo/memory-trace-topic-neighbourhoods-plan.md`.

# Proposal: Minimal Memory Trail Graph and Topic Neighbourhood Model for Memory Seed

## Status

**Proposed**

## Suggested Repository Path

```text
docs/3_Spec/memory-trail-graph-and-topic-neighbourhoods.md
```

## Purpose

This proposal defines a practical graph model for Memory Seed session entries and Memory Trace.

It folds together the following decisions:

1. Memory Seed entries should remain clean and human-readable.
2. Graph structure should be mostly derived, not hand-authored.
3. `related_entries` should remain the explicit memory-trail edge.
4. `topics` should be added as indexed, deterministic neighbourhood membership.
5. Memory Trace should render entry trails and topic neighbourhoods from the same retrieval and graph contracts used by MCP.
6. CLI and MCP tooling should validate the topic surface so users and agents can trust the graph.

---

## 1. Repository Context

Memory Seed is already designed as a portable, local, Markdown-based memory system for AI coding agents. Its purpose is to plant a small Markdown control plane into a project so agents can recover purpose, conventions, risks, decisions, and recent work without depending on hosted memory.

Memory Trace already exists as the intended companion UI: a local read-only browser interface for search, filters, timeline, graph, and reader/details views over Markdown session files, backed by a rebuildable local SQLite cache outside the repository.

The repository also already has a canonical retrieval surface in `memory_seed/retrieval.py`, which is described as the shared search/fetch contract for MCP, the deprecated Lense shim, and the standalone Memory Trace UI.

Therefore, this proposal does **not** introduce a heavy graph schema inside each entry. It formalises the small set of metadata that already fits the Memory Seed architecture.

Repository surfaces reviewed:

```text
README.md
pyproject.toml
memory_seed/retrieval.py
memory_seed/semantic_cache.py
memory_seed/core.py
memory_seed/seed/.memory-seed/skills/session_logging.md
memory-trace/pyproject.toml
memory-trace/memory_trace/lense.py
docs/2_Todo/3.0-plan.md
docs/2_Todo/memory-trace-distribution-plan.md
docs/2_Todo/related-entries-p2-mutation-plan.md
docs/3_Spec/graph-edge-contract.md
```

---

## 2. Core Decision

Adopt a lightweight, entry-centred graph model:

> Memory Seed entries should describe durable project memory. Memory Trace should derive graph structure from entry IDs, topics, links, timestamps, branches, commits, and chunks.

The entry remains the authored unit.

The chunk remains the retrieval/highlighting unit.

The graph remains a derived UI/index layer.

Markdown remains the source of truth.

---

## 3. The 80/20 Metadata Model

Each meaningful session entry should use this compact YAML shape:

```yaml
entry_id: mse_0123456789abcdef
user_initials: JN
agent_type: codex
agent_name: null
project_path: .
subproject_path: null
branch: feature/memory-trace
topics:
  - memory-trace
  - graph-trails
related_entries:
  - mse_abcdef0123456789
supersedes:
  - mse_1111111111111111
commits:
  - 0123456789abcdef0123456789abcdef01234567
```

The existing session logging skill already defines the entry YAML pattern around `entry_id`, `user_initials`, `agent_type`, `agent_name`, `project_path`, `subproject_path`, and `related_entries`.

This proposal adds one controlled field:

```yaml
topics:
  - memory-trace
  - graph-trails
```

### Required or recommended fields

| Field | Status | Purpose |
|---|---:|---|
| `entry_id` | Required | Stable node identity |
| heading timestamp | Required | Timeline ordering |
| `topics` | Recommended | Deterministic neighbourhood membership |
| `related_entries` | Recommended when known | Explicit memory-trail edge |
| `supersedes` | Optional | Typed decision-replacement edge |
| `commits` | Optional | Implementation evidence |
| `branch` | Optional | Historical workstream axis |
| `user_initials` / `user` | Recommended | Contributor attribution |
| `agent_type` / `agent_name` | Recommended | Agent attribution |

Do **not** add noisy machine-state fields such as:

```yaml
nodes: ...
edges: ...
chunk_hash: ...
embedding_hash: ...
relationship_confidence: ...
graph_layout: ...
```

Those belong in derived indexes, not in session entries.

---

## 4. Graph Model

### 4.1 Primary node

The default graph node should be:

```text
MemoryEntry
```

Memory Trace should not initially make `Chunk`, `Topic`, `User`, `File`, or `Branch` into mandatory first-class graph nodes. Those can appear as facets, filters, labels, or later optional nodes.

### 4.2 Retrieval unit

The retrieval system may still expose chunks.

The current retrieval implementation supports both entry and section granularity, and section matches can be rolled up into one visible entry-level result.

Rule:

> Entries are selectable. Chunks are searchable and highlightable.

---

## 5. Edge Types

### 5.1 Authored edges

These are written into entry YAML.

| Edge | Field | Meaning |
|---|---|---|
| `related` | `related_entries` | This entry relates to an earlier entry |
| `supersedes` | `supersedes` | This entry replaces or deprecates an earlier decision |
| `implements` | `commits` or commit trailer | This entry is implemented by a Git commit |

The current graph contract already requires `related_entries`, `supersedes`, and `commits` to remain distinct edge kinds rather than being merged.

### 5.2 Neighbourhood membership

This proposal adds:

| Field | Meaning |
|---|---|
| `topics` | This entry belongs to one or more deterministic topic neighbourhoods |

A topic is not the same as a direct relationship.

Two entries sharing a topic are neighbours, but they are not necessarily explicitly related.

### 5.3 Derived display edges

Memory Trace may derive display edges from existing metadata.

| Edge | Derived from | Meaning |
|---|---|---|
| `topic` | shared `topics` value | Entries in the same topic neighbourhood |
| `branch` | same `branch` value | Entries in the same workstream |
| `day` | same session date | Entries logged on the same day |
| `agent` | same agent | Entries by the same agent |
| `section` | heading paths | Matched section inside an entry |

The current Memory Trace graph implementation already derives `related`, `supersedes`, `topic`, `agent`, `day`, and `branch` edges.

This proposal formalises that behaviour.

---

## 6. Topic Index

Add a project-level topic index:

```text
.memory-seed/topics.yaml
```

Recommended shape:

```yaml
schema_version: 1

topics:
  - slug: memory-trace
    label: Memory Trace
    description: Local read-only UI for search, reader, timeline, graph, contributors, stats, and trail views.
    status: active
    aliases:
      - trace
      - lense
      - explorer

  - slug: graph-trails
    label: Graph Trails
    description: Related entries, topic neighbourhoods, branch chains, and Memory Trail graph semantics.
    status: active
    aliases:
      - memory-trail
      - graph-ui

  - slug: retrieval
    label: Retrieval
    description: MCP search, chunk extraction, ranking, semantic recall, lexical fallback, and fetch behaviour.
    status: active
    aliases:
      - search
      - memory-search
```

### Topic fields

| Field | Required | Purpose |
|---|---:|---|
| `slug` | Yes | Canonical machine-readable topic ID |
| `label` | Yes | Human display name |
| `description` | Yes | Boundary of the topic |
| `status` | Yes | `active`, `deprecated`, or `reserved` |
| `aliases` | Optional | Search, migration, and user convenience |

### Slug rules

Recommended format:

```text
[a-z0-9][a-z0-9-]{1,63}
```

Good:

```text
memory-trace
graph-trails
session-logging
multi-user
encoding-hygiene
```

Avoid:

```text
Memory Trace
memory_trace
trace/ui
retrieval.search
```

---

## 7. Topic Neighbourhood Semantics

A topic neighbourhood is the ordered set of entries that share a topic.

Example entry:

```yaml
topics:
  - memory-trace
  - graph-trails
```

This entry belongs to two deterministic neighbourhoods:

```text
memory-trace
graph-trails
```

Memory Trace should render these as timeline-aware trails:

```text
Topic: graph-trails

2026-07-04 - Graph edge contract
2026-07-05 - Memory Trace package decision
2026-07-08 - Minimal graph model
2026-07-08 - Topic neighbourhood proposal
```

### Important graph rule

Do **not** create a full mesh between every entry sharing a topic.

Instead, derive a chronological chain per topic:

```text
Entry A → Entry B → Entry C
```

This keeps the graph legible and avoids edge explosion.

---

## 8. Starter Topic Index for Memory Seed

The first `.memory-seed/topics.yaml` for the Memory Seed project can be seeded from the functionality audit where available.

I could not resolve `docs/functionality-audit.md` on the current default branch through the GitHub connector during this evaluation, so this proposal treats the functionality audit as a local or branch-specific source to use when present.

Recommended starter topics for Memory Seed:

```yaml
schema_version: 1

topics:
  - slug: control-plane
    label: Control Plane
    description: Seed files, AGENTS routing, project bootstrap, policy, runtime structure, and update behaviour.
    status: active
    aliases: [runtime, bootstrap]

  - slug: session-logging
    label: Session Logging
    description: Session entry format, append-only logging, DRAFT records, timestamps, and session hygiene.
    status: active
    aliases: [logs, entries]

  - slug: retrieval
    label: Retrieval
    description: Chunk extraction, MCP memory search, ranking, semantic recall, lexical fallback, and result contracts.
    status: active
    aliases: [search, mcp-search]

  - slug: graph-trails
    label: Graph Trails
    description: Related entries, supersession, topic neighbourhoods, branch chains, and Memory Trail graph semantics.
    status: active
    aliases: [memory-trail, graph-ui]

  - slug: memory-trace
    label: Memory Trace
    description: Local read-only UI, graph view, timeline, reader, search, stats, and companion distribution.
    status: active
    aliases: [trace, lense, explorer]

  - slug: multi-user
    label: Multi-user Sessions
    description: Participants, per-user session files, identity, migration, user filters, and contributor views.
    status: active
    aliases: [participants, per-user]

  - slug: links-integrity
    label: Link Integrity
    description: Entry IDs, related entry validation, supersession validation, commit references, and link checking.
    status: active
    aliases: [links-check, validation]

  - slug: skills
    label: Skills
    description: Skill registry, skill profiles, optional skill installation, and agent runbook loading.
    status: active
    aliases: [skill-registry, runbooks]

  - slug: hooks
    label: Hooks
    description: Session start, retrieval reminder, session log reminder, and agent lifecycle hook behaviour.
    status: active
    aliases: [agent-hooks, lifecycle]

  - slug: release-packaging
    label: Release and Packaging
    description: Package versions, PyPI publishing, Memory Trace distribution, CLI installation, and update flow.
    status: active
    aliases: [packaging, publishing]

  - slug: encoding-hygiene
    label: Encoding Hygiene
    description: UTF-8 without BOM, LF line endings, Unicode normalization, and project-owned text file handling.
    status: active
    aliases: [utf-8, text-files]

  - slug: decision-diagrams
    label: Decision Diagrams
    description: Optional Mermaid sidecars for spatial, temporal, or concurrent decision reasoning.
    status: active
    aliases: [diagrams, mermaid]
```

---

## 9. Session Logging Skill Update

Update:

```text
memory_seed/seed/.memory-seed/skills/session_logging.md
```

Add `topics` to the example entry YAML.

Current example:

```yaml
entry_id: mse_0123456789abcdef
user_initials: USER
agent_type: codex
agent_name: null
project_path: .
subproject_path: null
related_entries:
  - ms-db2d715c
```

Revised example:

```yaml
entry_id: mse_0123456789abcdef
user_initials: USER
agent_type: codex
agent_name: null
project_path: .
subproject_path: null
topics:
  - session-logging
  - graph-trails
related_entries:
  - ms-db2d715c
```

Add guidance:

```md
## Topics

Before writing a meaningful session entry, read `.memory-seed/topics.yaml` if present.

Add a `topics:` list to the entry YAML using canonical slugs from that index.

Use 1–3 topics by default. An entry may belong to multiple topics when the work genuinely touches multiple project areas.

Do not invent free-form topics. If no existing topic fits, add a new topic to `.memory-seed/topics.yaml` with a short label and description, then use that slug in the entry.

Run `memory-seed topics check` when adding or changing topics.
```

The existing session logging skill already says old logs should not be rewritten solely to match the newest schema unless the user explicitly asks. Apply the same rule to topics:

> New entries should use topics. Old entries should not be automatically backfilled unless the user requests curation.

---

## 10. Parser and Retrieval Changes

### 10.1 Extend `MemoryChunk`

The current `MemoryChunk` already carries fields including `chunk_id`, source path, session date, heading path, text, tags, contexts, line range, `entry_id`, user/agent metadata, `related_entries`, `supersedes`, `commits`, `branch`, sections, and granularity.

Add:

```python
topics: tuple[str, ...] = ()
```

### 10.2 Parse topics from entry YAML

Current extraction already reads entry YAML fields such as `entry_id`, `related_entries`, `supersedes`, `commits`, and `branch`.

Add:

```python
topics = _metadata_list(metadata, "topics")
```

Keep these separate:

| Field | Source | Meaning |
|---|---|---|
| `topics` | entry YAML | Controlled project topic index |
| `tags` | inline Markdown hashtags | Free-form local markers |
| `contexts` | heading paths | Derived structural context |

### 10.3 Expose topics in retrieval results

`memory_search` and `memory_get_chunk` should include:

```json
{
  "topics": ["retrieval", "graph-trails"]
}
```

### 10.4 Add topic filter

Add an optional retrieval filter:

```text
topic: string | null
```

The filter should apply before ranking, consistent with existing user/date filtering behaviour.

---

## 11. CLI Tooling

Add a topic command group:

```bash
memory-seed topics list
memory-seed topics check
memory-seed topics suggest --from docs/functionality-audit.md
```

### 11.1 `topics list`

Shows the indexed topic surface.

Example:

```text
Topic Index

active:
- retrieval          MCP search, chunk extraction, ranking...
- memory-trace       Local read-only UI...
- graph-trails       Related entries, topic neighbourhoods...

deprecated:
- lense              Use memory-trace instead.
```

### 11.2 `topics check`

Validates indexed topics against session entries.

Checks:

| Check | Severity |
|---|---|
| Missing `.memory-seed/topics.yaml` when entries use `topics` | Error |
| Entry topic not found in index | Error |
| Duplicate topic slug | Error |
| Malformed topic slug | Error |
| Deprecated topic used in new entry | Warning or strict-mode error |
| Alias collides with canonical slug | Warning |
| Entry has too many topics | Warning |
| Indexed topic unused | Warning |
| Topic index unreadable | Error |

Example output:

```text
Topic Check

Files checked: 14
Entries checked: 82
Topics indexed: 17
Topics used: 12

Errors:
- .memory-seed/sessions/2026-07-08/jean.md: mse_abc... uses unknown topic 'graph-ui'

Warnings:
- Indexed topic 'release-packaging' is unused.
```

### 11.3 `topics suggest`

Read-only helper:

```bash
memory-seed topics suggest --from docs/functionality-audit.md --output .memory-seed/topics.suggested.yaml
```

Rules:

1. Do not overwrite `.memory-seed/topics.yaml` by default.
2. Extract likely areas from a functionality audit, architecture document, or project index.
3. Output suggested topic slugs, labels, descriptions, and aliases.
4. Let the user or agent review before adopting.

---

## 12. Relationship to `links check`

The current `links check` already validates session-memory integrity across legacy and per-user layouts, including duplicate IDs, dangling `related_entries`, dangling `supersedes`, malformed commits, unknown commits, frontmatter problems, and diagram sidecar issues.

Topic validation should be separate but connected.

Recommended:

```bash
memory-seed topics check
```

Then `memory-seed doctor` may report:

```text
Topic index issues found. Run: memory-seed topics check
```

`links check` should not become the topic vocabulary validator unless a single all-integrity command is later wanted.

---

## 13. MCP Tooling

Add MCP topic tools so agents can verify the topic surface before writing or querying.

### 13.1 `memory_topics`

Returns indexed topics and optional usage counts.

Shape:

```json
{
  "topics": [
    {
      "slug": "retrieval",
      "label": "Retrieval",
      "description": "MCP search, chunk extraction, ranking, semantic recall, lexical fallback, and fetch behaviour.",
      "status": "active",
      "aliases": ["search", "memory-search"],
      "entry_count": 18
    }
  ]
}
```

### 13.2 `memory_topic_check`

Returns CLI-equivalent validation.

Shape:

```json
{
  "ok": false,
  "files_checked": 14,
  "entries_checked": 82,
  "topics_indexed": 17,
  "topics_used": 12,
  "errors": [
    {
      "file": ".memory-seed/sessions/2026-07-08/jean.md",
      "entry_id": "mse_abc...",
      "kind": "unknown-topic",
      "detail": "topic 'graph-ui' is not defined in .memory-seed/topics.yaml"
    }
  ],
  "warnings": []
}
```

### 13.3 `memory_search` topic filter

Extend:

```text
memory_search(query, topic="retrieval")
```

This supports agent recall within a deterministic neighbourhood.

---

## 14. Memory Trace UI Behaviour

Memory Trace should render topic neighbourhoods as first-class UI concepts.

The current Memory Trace API already exposes endpoints for runtime, facets, search, chunk, timeline, graph, and cache rebuild.

This proposal adds topic-aware behaviour on top.

### 14.1 Topic sidebar

```text
Topics
├── retrieval              18 entries
├── memory-trace           14 entries
├── graph-trails           11 entries
├── session-logging         9 entries
└── multi-user              7 entries
```

### 14.2 Topic trail view

```text
Topic: graph-trails

2026-07-04  Graph edge contract
2026-07-05  Memory Trace package decision
2026-07-08  Minimal graph model
2026-07-08  Topic neighbourhood proposal
```

### 14.3 Entry inspector

```text
Topics:
- memory-trace
- graph-trails
- session-logging

Related entries:
- mse_abcdef0123456789

Branch:
- feature/memory-trace
```

### 14.4 Graph defaults

Recommended default graph toggles:

```text
related_entries: on
supersedes: on
topics: on
branch: off
day: off
agent: off
```

This keeps the graph meaningful without visual noise.

---

## 15. Memory Trail View

Add a dedicated trail mode or endpoint after the graph contract is documented.

Recommended endpoint:

```text
GET /api/trail?entry_id=...&axis=related|topic|branch|day|implementation
```

Response shape:

```json
{
  "entry_id": "mse_0123456789abcdef",
  "axis": "topic",
  "topic": "graph-trails",
  "entries": [
    {
      "entry_id": "mse_old...",
      "title": "Graph edge contract",
      "date": "2026-07-04",
      "edge": "topic"
    },
    {
      "entry_id": "mse_current...",
      "title": "Topic neighbourhood proposal",
      "date": "2026-07-08",
      "edge": "selected"
    }
  ],
  "side_edges": [
    {
      "source": "mse_current...",
      "target": "mse_other...",
      "type": "related"
    }
  ]
}
```

Trail axes:

| Axis | Source |
|---|---|
| `related` | `related_entries` and inbound backlinks |
| `topic` | `topics` |
| `branch` | `branch` |
| `day` | session date |
| `implementation` | `commits` and commit trailers |
| `supersession` | `supersedes` and `superseded_by` |

---

## 16. Generated Indexes and Cache

Do not commit graph databases or vector indexes as authoritative state.

Allowed derived stores:

```text
.memory-seed/index/
  graph.json
  topics.json
  trails.json
```

or Memory Trace’s external local cache.

Rules:

1. Generated indexes are rebuildable.
2. Markdown remains authoritative.
3. SQLite remains outside the repository or gitignored.
4. UI layout state does not belong in session entries.
5. Embedding metadata does not belong in session entries.
6. Inferred relationships do not belong in session entries by default.

---

## 17. Implementation Plan

### Phase 1 — Spec and seed files

1. Create:

```text
docs/3_Spec/memory-trail-graph-and-topic-neighbourhoods.md
```

2. Create:

```text
.memory-seed/topics.yaml
```

3. Update session logging skill to include `topics`.
4. Add starter topic index for Memory Seed.
5. Add topic guidance to Memory Trail proposal/spec.

### Phase 2 — Parser and retrieval

1. Add `topics` to `MemoryChunk`.
2. Parse `topics:` from entry YAML.
3. Expose `topics` in `memory_search`.
4. Expose `topics` in `memory_get_chunk`.
5. Add optional `topic` filter.
6. Keep `topics`, `tags`, and `contexts` distinct.

### Phase 3 — CLI

Add:

```bash
memory-seed topics list
memory-seed topics check
memory-seed topics suggest
```

Minimum viable CLI:

```bash
memory-seed topics check
```

### Phase 4 — MCP

Add:

```text
memory_topics
memory_topic_check
```

Optional:

```text
memory_search(..., topic="retrieval")
```

### Phase 5 — Memory Trace

1. Add topic facet counts.
2. Add topic filter.
3. Add topic trail view.
4. Add graph edge toggle for topics.
5. Add unknown-topic warning if topic validation fails.
6. Keep UI read-only.

### Phase 6 — Curation

Keep curation CLI-first.

The existing Related Entries P2 plan proposes conservative mutation helpers such as `memory-seed link add`, while explicitly avoiding automatic graph generation and Memory Trace write features.

Apply the same principle to topics:

1. Topic suggestions are read-only by default.
2. Topic index updates should be explicit.
3. Historical topic backfill should require user intent.
4. Memory Trace should not silently mutate session files.

---

## 18. Acceptance Criteria

The proposal is implemented when:

1. New session entries may include `topics:`.
2. `.memory-seed/topics.yaml` defines the valid topic surface.
3. The session logging skill instructs agents to use indexed topics.
4. CLI can list topics.
5. CLI can validate unknown, malformed, duplicate, deprecated, and unused topics.
6. MCP can expose the topic index.
7. MCP can expose topic validation results.
8. Retrieval results include explicit `topics`.
9. Retrieval supports optional topic filtering.
10. Memory Trace can filter by topic.
11. Memory Trace can render topic neighbourhood trails.
12. Entries may belong to multiple topic neighbourhoods.
13. Old entries without `topics` remain valid.
14. No heavy graph metadata is added to session entries.
15. Generated graph/cache data remains rebuildable and non-authoritative.
16. `related_entries`, `supersedes`, `commits`, `branch`, and `topics` keep distinct meanings.
17. Topic graph edges are rendered as chronological chains, not full meshes.
18. Memory Trace remains read-only.

---

## 19. Risks and Mitigations

### Risk: Topic sprawl

Too many topics can make the surface noisy.

Mitigation:

- use a controlled topic index;
- recommend 1–3 topics per entry;
- warn on unused or near-duplicate topics;
- use aliases rather than creating duplicate slugs.

### Risk: Agents invent topics

Agents may create free-form topics during logging.

Mitigation:

- session logging skill must tell agents to read `.memory-seed/topics.yaml`;
- `topics check` catches unknown topics;
- MCP exposes `memory_topics`.

### Risk: Topic graph becomes too dense

If every shared topic creates edges between every pair, the graph becomes unreadable.

Mitigation:

- topic neighbourhoods are chronological chains, not complete meshes.

### Risk: Old entries lack topics

Historical entries may not participate in topic neighbourhoods.

Mitigation:

- old entries remain valid;
- topic backfill is optional curation;
- semantic search and related links still work.

### Risk: Topic index becomes stale

The project evolves but topic index does not.

Mitigation:

- `topics check` warns on unused topics;
- `topics suggest --from docs/functionality-audit.md` can propose updates;
- Memory Trace can show topic usage counts.

---

## 20. Final Recommendation

Adopt the following model:

```text
related_entries = explicit memory trail
topics = deterministic neighbourhoods
branch = workstream axis
supersedes = decision replacement
commits = implementation evidence
chunks = retrieval/highlighting units
Memory Trace graph = derived read-only view
```

The revised 80/20 entry model is:

```yaml
entry_id: mse_0123456789abcdef
user_initials: JN
agent_type: codex
agent_name: null
project_path: .
subproject_path: null
branch: main
topics:
  - retrieval
  - graph-trails
related_entries:
  - mse_abcdef0123456789
supersedes: []
commits: []
```

This gives Memory Seed a smooth and practical graph foundation without making session entries noisy.

It also gives Memory Trace two complementary ways to build memory trails:

1. **Explicit trails** through `related_entries`.
2. **Deterministic neighbourhoods** through indexed `topics`.

That is the useful 20% that provides most of the graph UI value.
