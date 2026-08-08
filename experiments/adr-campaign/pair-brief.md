# Pair evaluation brief (2026-08-08)

Each item is a PAIR: two decisions linked by one lifecycle edge, sharing a topic area. A pair is
weaker evidence than a chain - two decisions touching the same area may be a standing concern, or
may simply be two decisions. **Your first job is to decide which.**

## Step 1 - is this architectural?

Read BOTH decisions. Grep the entry_id (before `:dN`) under `.memory-seed/sessions/`, then read
that decision's `#### Dn` block (or `### Decision` for a single-decision entry).

Answer `architectural: true` only if a reader would expect this recorded as a STANDING CONCERN -
something that governs how the project works and that a future decision would need to respect.

Answer `architectural: false` when the pair is:
- two instances of applying an existing rule, rather than the rule itself
- routine implementation or a bugfix and its follow-up
- work already governed by an existing ADR (say which in `note`)
- coincidental: same area, but answering unrelated questions

**`false` is a perfectly good answer and most pairs may deserve it.** A weak ADR costs more than a
missing one: it claims a concern exists where none does, and every future decision has to route
around it.

## Step 2 - only if architectural, draft the ADR

- `title`: what the concern IS. A colon is fine.
- `decision` (<=650), `why` (<=650), `evolution` (<=400): from the two decisions only.
- `topics`: 1-3 from the CANONICAL list. `constitution_refs`: one `governing`, optional
  `supporting`, from the ANCHOR list. NEVER mix the two vocabularies.
- `quote` (40-160 chars) copied verbatim from one member's body, with `quote_ref` naming which.
- `head` is given. Do not change it.

## Output contract

ONLY a JSON array, one object per pair:

{"suggested_head": "<copied>", "architectural": true|false, "note": "one sentence either way",
  "adr_id": "adr_<snake>", "title": "...", "topics": [...], "decision": "...", "why": "...",
  "evolution": "...", "constitution_refs": [{"ref": "...", "role": "governing"}],
  "quote": "...", "quote_ref": "..."}

When `architectural` is false, give `suggested_head`, `architectural`, `note` and nothing else.

## CANONICAL TOPIC LIST
["agent-collaboration", "agent-rules", "backfill", "branch-history", "bugfix", "changelog", "cleanup", "cli", "continuity", "control-plane", "decision-harvest", "design-evaluation", "diagram-view", "docs-lifecycle", "document-ingestion", "documentation", "feature-build", "functionality-audit", "git-publishing", "git-workflow", "goal", "governance-profile", "graph", "hooks", "inspector", "lazy-loading", "licensing", "lifecycle-edges", "mcp-tools", "memory-repair", "memory-trace", "merge", "mermaid", "migration", "multi-user-sessions", "navigation", "package", "panes", "performance", "process-correction", "process-management", "proposal", "proposal-lifecycle", "readme", "related-entries", "release", "release-packaging", "release-preflight", "retrieval", "roadmap", "schema", "security", "seed-core", "session-fuse", "session-layout", "session-logging", "skill-architecture", "supersession", "test-suite", "testing", "tooling-evaluation", "topbar", "topic-vocabulary", "trace-cache", "trace-harness", "trail", "ui-design", "upgrade-workflow", "windows-encoding"]

## ANCHOR LIST
["constitution:v1#append-only", "constitution:v1#authority", "constitution:v1#draft-format", "constitution:v1#edge-kinds", "constitution:v1#evidence-first", "constitution:v1#explainability", "constitution:v1#expose-before-rank", "constitution:v1#folder-lifecycle", "constitution:v1#immediate-value", "constitution:v1#integration-mode", "constitution:v1#link-corrections", "constitution:v1#markdown-authority", "constitution:v1#metadata-curation", "constitution:v1#minimal-context", "constitution:v1#model-independence", "constitution:v1#open-core", "constitution:v1#ownership", "constitution:v1#prove-automation", "constitution:v1#provenance", "constitution:v1#retrieval-transparency", "constitution:v1#single-source", "constitution:v1#topic-vocabulary", "constitution:v1#trust-first", "constitution:v1#write-surface-parity"]
