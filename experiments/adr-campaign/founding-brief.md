# ADR founding brief - chains (2026-08-08)

Each item you are given is a LINEAGE CHAIN: decisions connected by recorded evolves/replaces edges
that all share one topic area. The chain IS the concern. Your job is to write the ADR that records
it.

## For each chain

1. Read every member decision. Grep its entry_id (the part before `:dN`) under
   `.memory-seed/sessions/`, then read that decision's `#### Dn` block (or `### Decision` for a
   single-decision entry). The chain is ordered oldest to newest.
2. Write:
   - `title`: what the concern IS, not what one decision did. A colon is fine.
   - `decision` (<=650 chars): the current position, present tense, specific. If the chain covers
     more than one thread, say all of them - a title covering one thread misdescribes the rest.
   - `why` (<=650): the reasoning the members give. Not invented.
   - `evolution` (<=400): how it developed across the chain, oldest to newest, with dates.
3. `topics`: 1-3 slugs from the CANONICAL list. The chain's own area is usually one of them.
4. `constitution_refs`: exactly one `governing`, optionally one `supporting`, from the ANCHOR list.
5. `quote`: 40-160 verbatim characters from ONE member's decision body, proving you read it. Copy
   it, do not retype it. Say which ref it came from in `quote_ref`.

## Rules

- `head` is given to you. Do not change it.
- Every ref you output must be copied EXACTLY from the chain's member list. Never invent one.
- NEVER put a constitution slug in `topics`, or a topic slug in `constitution_refs`. They are
  different vocabularies and mixing them dropped 6 ADRs in an earlier run.
- If a chain does not read as one coherent concern, say so in `note` and still draft your best
  reading - a human decides, not you.

## Output contract

ONLY a JSON array, one object per chain, no prose outside it:

{"area": "...", "adr_id": "adr_<lowercase_snake>", "title": "...", "head": "<copied>",
  "topics": [...], "decision": "...", "why": "...", "evolution": "...",
  "constitution_refs": [{"ref": "constitution:v1#...", "role": "governing"}],
  "quote": "...", "quote_ref": "...", "note": ""}

## CANONICAL TOPIC LIST (only legal values for `topics`)
["agent-collaboration", "agent-rules", "backfill", "branch-history", "bugfix", "changelog", "cleanup", "cli", "continuity", "control-plane", "decision-harvest", "design-evaluation", "diagram-view", "docs-lifecycle", "document-ingestion", "documentation", "feature-build", "functionality-audit", "git-publishing", "git-workflow", "goal", "governance-profile", "graph", "hooks", "inspector", "lazy-loading", "licensing", "lifecycle-edges", "mcp-tools", "memory-repair", "memory-trace", "merge", "mermaid", "migration", "multi-user-sessions", "navigation", "package", "panes", "performance", "process-correction", "process-management", "proposal", "proposal-lifecycle", "readme", "related-entries", "release", "release-packaging", "release-preflight", "retrieval", "roadmap", "schema", "security", "seed-core", "session-fuse", "session-layout", "session-logging", "skill-architecture", "supersession", "test-suite", "testing", "tooling-evaluation", "topbar", "topic-vocabulary", "trace-cache", "trace-harness", "trail", "ui-design", "upgrade-workflow", "windows-encoding"]

## ANCHOR LIST (only legal values for `constitution_refs[].ref`)
["constitution:v1#append-only", "constitution:v1#authority", "constitution:v1#draft-format", "constitution:v1#edge-kinds", "constitution:v1#evidence-first", "constitution:v1#explainability", "constitution:v1#expose-before-rank", "constitution:v1#folder-lifecycle", "constitution:v1#immediate-value", "constitution:v1#integration-mode", "constitution:v1#link-corrections", "constitution:v1#markdown-authority", "constitution:v1#metadata-curation", "constitution:v1#minimal-context", "constitution:v1#model-independence", "constitution:v1#open-core", "constitution:v1#ownership", "constitution:v1#prove-automation", "constitution:v1#provenance", "constitution:v1#retrieval-transparency", "constitution:v1#single-source", "constitution:v1#topic-vocabulary", "constitution:v1#trust-first", "constitution:v1#write-surface-parity"]
