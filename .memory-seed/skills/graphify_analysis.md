---
memory-system-version: 2.19
governing_adr: adr_optional_skill_profiles
tags: [memory-seed, skill, graphify]
---

# Graphify Structural Analysis

Use Graphify after Semble when the task needs architecture, dependency impact, call-path, or community-level evidence rather than a routine code lookup.

## Procedure

1. Check `graphify --help` and find `graphify-out/graph.json` at the target root.
2. If it is absent or stale, run `graphify extract <target> --code-only`. This creates only local, regenerable structural output; `graphify-out/` stays ignored.
3. Use `graphify query`, `path`, `affected`, `explain`, or `god-nodes` for the concrete question.
4. Treat output as structural evidence, not proof of product intent; confirm consequential conclusions in source and tests.
5. Do not use semantic extraction, community labeling, or a provider backend without explicit approval: those may send repository content externally.

## Boundaries

- Semble remains the default for semantic/symbol code search.
- Rebuild on demand; do not commit generated graph output unless the user explicitly requests an artifact.
- If Graphify is unavailable, report that and fall back to Semble plus direct source inspection.
