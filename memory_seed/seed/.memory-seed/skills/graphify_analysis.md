---
memory-system-version: 2.22
governing_adr: adr_optional_skill_profiles
tags: [memory-seed, skill, graphify]
---

# Graphify Structural Analysis

Use Graphify after Semble when the task needs architecture, dependency impact, call-path, or community-level evidence rather than a routine code lookup.

## Procedure

1. Check whether `.memory-seed/project.yaml` opts into `graphify_merge_refresh: true`.
2. For an opted-in project, run `python -m memory_seed.graphify_refresh status` before trusting
   `graphify-out/graph.json`. Use `python -m memory_seed.graphify_refresh query "<question>"` for
   freshness-guarded retrieval. After selected documents are committed, use
   `python -m memory_seed.graphify_refresh refresh` to recover from a failed merge refresh.
   Do not run a code-only extract over this managed documentation index.
3. Otherwise, check `graphify --help` and find `graphify-out/graph.json` at the target root. If it
   is absent or stale, run `graphify extract <target> --code-only`. This creates only local,
   regenerable structural output; `graphify-out/` stays ignored.
4. Use available Graphify query, path, affected, explain, or god-nodes operations for the concrete
   question. Treat output as structural evidence, not proof of product intent; confirm
   consequential conclusions in source and tests.
5. Do not use semantic extraction, community labeling, or a provider backend without explicit
   approval: those may send repository content externally.

## Boundaries

- Semble remains the default for semantic/symbol code search.
- The merge-managed index is opt-in, local, deterministic, and regenerable. Do not commit generated
  graph output unless the user explicitly requests an artifact.
- If Graphify is unavailable, report that and fall back to Semble plus direct source inspection.
