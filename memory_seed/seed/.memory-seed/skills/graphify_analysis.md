---
memory-system-version: 2.22
governing_adr: adr_optional_skill_profiles
tags: [memory-seed, skill, graphify]
---

# Graphify Structural Analysis

Use Graphify after Semble when code work needs architecture, dependency impact, call-path, or
community-level evidence rather than a routine lookup. For questions about relationships among
indexed project documents, use the local graph as a structural lead before inspecting the source
Markdown. Read a single document directly for ordinary content questions.

## Procedure

1. Check whether `.memory-seed/project.yaml` opts into `graphify_merge_refresh: true`.
2. For a document-relationship question, first confirm the documents are within the opted-in
   project's `.graphifyignore` scope. Run `python -m memory_seed.graphify_refresh status` before
   trusting `graphify-out/graph.json`, then use
   `python -m memory_seed.graphify_refresh query "<question>"` for freshness-guarded retrieval.
   Follow structural links or references to the source Markdown and verify any claimed dependency
   or impact there; the graph does not prove intent or infer decision semantics. If the index is
   absent, stale, unavailable, or the documents are outside its scope, inspect the documents
   directly rather than creating a code-only graph.
3. For an opted-in project after selected documents are committed, use
   `python -m memory_seed.graphify_refresh refresh` to recover from a failed merge refresh.
   Do not run a code-only extract over this managed documentation index.
4. For structural code analysis in a project without the managed index, check `graphify --help`
   and find `graphify-out/graph.json` at the target root. If absent or stale, run
   `graphify extract <target> --code-only`. This creates only local,
   regenerable structural output; `graphify-out/` stays ignored.
5. Use available Graphify query, path, affected, explain, or god-nodes operations for the concrete
   question. Treat output as structural evidence, not proof of product intent; confirm
   consequential conclusions in source and tests.
6. Do not use semantic extraction, community labeling, or a provider backend without explicit
   approval: those may send repository content externally.

## Boundaries

- Semble remains the default for semantic/symbol code search.
- The merge-managed index is opt-in, local, deterministic, and regenerable. Do not commit generated
  graph output unless the user explicitly requests an artifact.
- If Graphify is unavailable, report that and fall back to Semble plus direct source inspection.
