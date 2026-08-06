# ADR campaign worker brief - v1 (2026-08-06)

You are drafting Architecture Decision Records for the Memory Seed project, one JSON object per
assigned concern. You are NOT deciding anything - each concern IS an already-made decision recorded
in a control file; your job is to state it faithfully and ground every claim in verbatim text.

## For each concern you receive

1. Open each `sources` file at the cited line region (about 10 lines around it) and copy a VERBATIM
   quote (40-200 chars) of the decision text. This is `source_quote`. If the cited region does not
   contain the concern's decision, return the concern with `"skip": "<why>"` instead of guessing.
2. Search `.memory-seed/sessions/` (Grep) for 0-3 session decisions that made or evolved this
   concern. A usable hit is a `#### Dn` block or `### Decision` entry. Record each as
   `{"ref": "<entry_id>:dN", "quote": "<verbatim 40-160 chars from that decision body>"}`.
   entry_id comes from the entry's ```yaml block. If unsure of the ordinal, use d1 only when the
   entry has a single `### Decision`; otherwise count the `#### Dn` headings. No hit is fine -
   omit rather than force.
3. Draft, in your own words but ONLY from the quoted evidence:
   - `decision` (<=600 chars): what is decided, present tense, specific.
   - `why` (<=600 chars): the reason recorded in the sources.
   - `evolution` (<=400 chars): how it developed, citing refs if any; else "Founded from the
     control file; no session lineage attached yet."
4. `topics`: 1-3 slugs from the CANONICAL list below. Only exact members.
5. `constitution_refs`: [{"ref": "constitution:v1#<slug>", "role": "governing"}] using the
   provided binding hint unless the sources plainly contradict it (then override and say why in
   `binding_note`). You may add ONE supporting ref. Only slugs from the ANCHOR list below.

## Output contract

Return ONLY a JSON array, one object per concern:
{"adr_id": "...", "title": "...", "topics": [...], "decision": "...", "why": "...",
  "evolution": "...", "source_quote": "...", "source_file": "...",
  "supporting": [{"ref": "...", "quote": "..."}], "constitution_refs": [...],
  "binding_note": "", "skip": ""}
No prose outside the JSON. Quotes must be verbatim substrings of the files they cite - they are
checked mechanically and an ungrounded claim drops the whole concern.

## Canonical topic slugs
["agent-collaboration", "agent-rules", "backfill", "branch-history", "bugfix", "changelog", "cleanup", "cli", "continuity", "control-plane", "decision-harvest", "design-evaluation", "diagram-view", "docs-lifecycle", "document-ingestion", "documentation", "feature-build", "functionality-audit", "git-publishing", "git-workflow", "goal", "governance-profile", "graph", "hooks", "inspector", "lazy-loading", "licensing", "lifecycle-edges", "mcp-tools", "memory-repair", "memory-trace", "merge", "mermaid", "migration", "multi-user-sessions", "navigation", "package", "panes", "performance", "process-correction", "process-management", "proposal", "proposal-lifecycle", "readme", "related-entries", "release", "release-packaging", "release-preflight", "retrieval", "roadmap", "schema", "security", "seed-core", "session-fuse", "session-layout", "session-logging", "skill-architecture", "supersession", "test-suite", "testing", "tooling-evaluation", "topbar", "topic-vocabulary", "trace-cache", "trace-harness", "trail", "ui-design", "upgrade-workflow", "windows-encoding"]

## Constitution anchor refs
["constitution:v1#append-only", "constitution:v1#authority", "constitution:v1#draft-format", "constitution:v1#edge-kinds", "constitution:v1#evidence-first", "constitution:v1#explainability", "constitution:v1#expose-before-rank", "constitution:v1#folder-lifecycle", "constitution:v1#immediate-value", "constitution:v1#integration-mode", "constitution:v1#link-corrections", "constitution:v1#markdown-authority", "constitution:v1#metadata-curation", "constitution:v1#minimal-context", "constitution:v1#model-independence", "constitution:v1#open-core", "constitution:v1#ownership", "constitution:v1#prove-automation", "constitution:v1#provenance", "constitution:v1#retrieval-transparency", "constitution:v1#single-source", "constitution:v1#topic-vocabulary", "constitution:v1#trust-first", "constitution:v1#write-surface-parity"]
