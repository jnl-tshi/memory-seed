# ADR campaign worker brief - v2 (2026-08-06)

v1 lost 12 of 34 concerns to two brief defects, both fixed here: (a) workers used constitution
slugs in the `topics` field - the two vocabularies are now kept apart; (b) long quotes drifted in
their tails - quotes are now SHORT and verified.

You are drafting Architecture Decision Records for Memory Seed. You are NOT deciding anything -
each concern IS an already-made decision recorded in a control file. State it faithfully and
ground every claim in verbatim text.

## THE TWO VOCABULARIES ARE DIFFERENT. DO NOT MIX THEM.

- `topics` -> ONLY slugs from the CANONICAL TOPIC LIST at the bottom. These are project subject
  tags (e.g. "control-plane", "retrieval"). If no listed slug fits, return FEWER topics - an empty
  list is fine. NEVER invent one.
- `constitution_refs` -> ONLY "constitution:v1#..." refs from the ANCHOR LIST. These are governance
  clauses. A constitution slug like "authority" or "provenance" is NEVER a topic.

## Quotes: short and verified

1. Read the file and copy a SHORT run of text: 40-120 characters, ideally within ONE line.
2. Prefer the start of a sentence or bullet. Do NOT quote across a line wrap - the tail is where
   transcription drifts, and a drifted quote drops the whole concern.
3. Before returning, re-read the file and confirm your quote appears character-for-character.

## For each concern

1. `source_quote` + `source_file`: a short verified quote from one of the concern's `sources`
   files. `source_file` is the BARE path, no "#L" fragment. Mandatory.
2. `supporting`: pick 0-2 refs FROM THE PROVIDED `candidate_refs` LIST ONLY. Never write a ref not
   in that list - invented refs were the biggest failure of the last run. For each, read that
   decision (Grep its entry_id under .memory-seed/sessions/) and quote 40-120 verified characters
   from its body. If the candidates are irrelevant, return an empty list. No attachments is fine.
3. `decision` (<=600 chars), `why` (<=600), `evolution` (<=400): your own words, from quoted
   evidence only. With no session lineage, evolution is "Founded from the control file; no session
   lineage attached yet."
4. `constitution_refs`: one governing ref (use the concern's `binding` hint unless the source
   plainly contradicts it), optionally one supporting.

## Output contract

ONLY a JSON array, one object per concern, no prose outside it:
{"adr_id": "...", "title": "...", "topics": [...], "decision": "...", "why": "...",
  "evolution": "...", "source_quote": "...", "source_file": "...",
  "supporting": [{"ref": "...", "quote": "..."}], "constitution_refs": [...],
  "binding_note": "", "skip": ""}

## CANONICAL TOPIC LIST (the only legal values for `topics`)
["agent-collaboration", "agent-rules", "backfill", "branch-history", "bugfix", "changelog", "cleanup", "cli", "continuity", "control-plane", "decision-harvest", "design-evaluation", "diagram-view", "docs-lifecycle", "document-ingestion", "documentation", "feature-build", "functionality-audit", "git-publishing", "git-workflow", "goal", "governance-profile", "graph", "hooks", "inspector", "lazy-loading", "licensing", "lifecycle-edges", "mcp-tools", "memory-repair", "memory-trace", "merge", "mermaid", "migration", "multi-user-sessions", "navigation", "package", "panes", "performance", "process-correction", "process-management", "proposal", "proposal-lifecycle", "readme", "related-entries", "release", "release-packaging", "release-preflight", "retrieval", "roadmap", "schema", "security", "seed-core", "session-fuse", "session-layout", "session-logging", "skill-architecture", "supersession", "test-suite", "testing", "tooling-evaluation", "topbar", "topic-vocabulary", "trace-cache", "trace-harness", "trail", "ui-design", "upgrade-workflow", "windows-encoding"]

## ANCHOR LIST (the only legal values for `constitution_refs[].ref`)
["constitution:v1#append-only", "constitution:v1#authority", "constitution:v1#draft-format", "constitution:v1#edge-kinds", "constitution:v1#evidence-first", "constitution:v1#explainability", "constitution:v1#expose-before-rank", "constitution:v1#folder-lifecycle", "constitution:v1#immediate-value", "constitution:v1#integration-mode", "constitution:v1#link-corrections", "constitution:v1#markdown-authority", "constitution:v1#metadata-curation", "constitution:v1#minimal-context", "constitution:v1#model-independence", "constitution:v1#open-core", "constitution:v1#ownership", "constitution:v1#prove-automation", "constitution:v1#provenance", "constitution:v1#retrieval-transparency", "constitution:v1#single-source", "constitution:v1#topic-vocabulary", "constitution:v1#trust-first", "constitution:v1#write-surface-parity"]
