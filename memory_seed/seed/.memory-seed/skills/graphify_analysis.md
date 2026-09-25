---
memory-system-version: 2.22
governing_adr: adr_optional_skill_profiles
tags: [memory-seed, skill, graphify]
---

# Graphify Structural Analysis

Use Graphify after Semble when code work needs architecture, dependency impact, call-path, or
community-level evidence rather than a routine lookup. For questions about relationships among
indexed project files, use the local graph as a structural lead before inspecting source files.
Read a single file directly for ordinary content questions.

## Procedure

1. Check whether `.memory-seed/project.yaml` opts into `graphify_merge_refresh: true`.
2. For a project-relationship question, first confirm the files are within the opted-in
   project's `.graphifyignore` scope. The shipped scope covers visible source code and Markdown
   throughout the project, including `docs/`, `experiments/`, `business/`, and demos. Any path
   component beginning with `.` is outside scope, including `.memory-seed/`; generated graph
   output and bulky data files are outside scope too. Session logs and decisions remain available
   through Memory Seed, not this graph. Run `python -m memory_seed.graphify_refresh status` before
   trusting `graphify-out/graph.json`, then use
   `python -m memory_seed.graphify_refresh query "<question>"` for freshness-guarded retrieval.
   Follow structural links or references to the source files and verify any claimed dependency
   or impact there; the graph does not prove intent or infer decision semantics. If the index is
   absent, stale, unavailable, or files are outside its scope, inspect source directly.
3. The seeded `.graphifyignore` is a passive, project-owned scope template; it does not enable a
   build. Only an explicit `graphify_merge_refresh: true` in `.memory-seed/project.yaml` opts a
   project into merge refresh. Scope changes cause a full rebuild; subsequent selected Git diffs
   update incrementally and retain unchanged contributions. For an opted-in project, after selected
   files are committed, use `python -m memory_seed.graphify_refresh refresh` to recover from a failed merge refresh.
   Do not run a code-only extract over this managed project index.
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
