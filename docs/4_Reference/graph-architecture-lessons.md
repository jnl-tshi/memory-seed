---
memory-system-version: 2.17
tags:
  - memory-seed
  - reference
  - graph
  - memory-trace
---

# Graph Architecture Lessons

Status: Reference
Source: Refined from `docs/2_Todo/completed/graph recommendations.md` on 2026-07-08.
Used by: `docs/2_Todo/memory-trace-topic-neighbourhoods-plan.md`

## Summary

The useful lesson is not "add a graph database." The useful lesson is to keep Markdown session
entries authoritative, derive graph structures as rebuildable indexes, and match graph-engine
complexity to the actual query depth.

## Lessons

- Separate the data structure from the visualization. Memory Trace can provide a strong graph
  experience from in-memory adjacency lists and frontend rendering without making a graph database
  authoritative.
- Match engine complexity to query depth. One-hop links, backlinks, supersession, branch chains,
  day chains, agent chains, and topic neighbourhoods should stay as cheap local indexes. Native graph
  databases are only justified for deep traversal, variable-length pathfinding, or network analytics.
- Preserve Markdown portability. Plain-text session files are the durable source of truth; graph
  indexes and UI layouts should be disposable and rebuildable.
- Treat memory as the scaling constraint. Local graph traversal is fast while the topology fits in
  RAM. If the corpus grows substantially, Memory Trace should improve cache/index strategy before
  changing the source-of-truth model.
- Avoid edge explosion. Topic neighbourhoods should render chronological chains or scoped local
  neighbourhoods, not full meshes between every entry that shares a topic.

## Implication

The right Memory Seed graph posture is lightweight and derived:

```text
Markdown entries -> parsed chunks -> canonical graph reader -> Trace UI/cache
```

Do not introduce a committed graph database, hidden graph state, or automatic history rewrite as the
first answer to graph UX needs.
