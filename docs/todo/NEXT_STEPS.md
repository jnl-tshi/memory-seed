# Next Steps

These items need user judgement, account access, or real-client validation.

## Active Roadmap

Approved 2026-06-13. Incremental release history has moved from 2.6.0 through the current 2.13.0
release. Source: docs/todo review + session findings.

### Release 2.6.0 (shipped 2026-06-13)

Bundles the SessionStart orientation hook (Claude/Codex/Gemini/Cursor) and Copilot CLI support, plus:

- **Gemini dead-wiring fix:** Gemini uses `AfterAgent` / `BeforeAgent`, not Claude-style
  `Stop` / `UserPromptSubmit`.
- **Copilot VS Code surface:** `.vscode/mcp.json` plus a thin `.github/copilot-instructions.md`
  router.
- **Hygiene:** current-state wording, recency-vs-topical retrieval guidance, and install docs.
- **Release mechanics:** 2.5 -> 2.6 package/control-plane bump, changelog, README, demo refresh,
  archive snapshot, and publish.

### Release 2.7.0 (shipped 2026-06-14)

- **Orphan & dead-artifact review:** diff-scoped orphan/artifact sweep added to the End Of Turn
  routine and mirrored in `/esr`; deterministic orphan-skill warning added to `doctor`.
- **Seed promotions:** `document_ingestion` and `office_document_editing` skills ported into the
  seed + live runtime with trigger-registry entries; Working Principles added to `agent-rules.md`.
- **ESR generalization:** later completed in 2.11.0.

### Release 2.8.0 (shipped 2026-06-14)

- **Non-destructive routing into foreign entry-point files:** routing files follow the greenfield /
  owned / foreign-with-markers / foreign-without-markers ownership branch in `init` and `update`.
- **Behavior change:** versionless entry-point files are merged, not overwritten.
- **Doctor route-presence backstop:** a `.memory-seed/` runtime whose present entry-point file is
  foreign-without-block is flagged as orphaned.

### Release 2.9.0 (shipped 2026-06-14)

- **Multi-user session dual-read discovery:** package readers discover both legacy flat files
  (`.memory-seed/sessions/YYYY-MM-DD.md`) and per-day/per-user files
  (`.memory-seed/sessions/YYYY-MM-DD/<user>.md`).

### Release 2.10.0 (shipped 2026-06-15)

- **User-aware session targets:** local user identity is opt-in through `.memory-seed/local.yaml`,
  `MEMORY_SEED_USER`, or `memory-seed session target --user`. New per-user targets are
  `.memory-seed/sessions/YYYY-MM-DD/<user>.md`.
- **User-aware hooks:** `session-log-check.py` checks only the active user's file, and
  `session-start-context.py` injects the active user's newest entry plus same-day co-contributor file
  counts.

### Release 2.11.0 (shipped 2026-06-15)

- **ESR generalization:** the End Of Turn routine now runs consolidation review and baseline-promotion
  checks. Seeded `/esr` command shortcuts ship for Claude and Gemini; Codex/Cursor use the routine in
  `agent-rules.md`.
- **Remaining optional:** seed `/esr` command shortcuts for Codex/Cursor once those tools support
  repo-level custom commands.

### Release 2.12.0 (shipped 2026-06-15)

First batch of multi-user Phase 3 increments from the reviewed 3.0 plan
([`3.0-plan.md`](3.0-plan.md)):

- **Session-memory integrity validation (A-P3):** `memory-seed links check` validates both layouts
  (duplicate `entry_id`/`hash_id`, dangling `related_*` refs incl. entry-level `related_entries`,
  per-user frontmatter user/date/schema/hash problems), names file + offending value, exits non-zero as
  a CI gate; `doctor` surfaces a one-line summary.
- **80-bit entry IDs (A-ID):** new generated `entry_id`s use deterministic `mse_` 80-bit Base32 IDs;
  legacy `ms-` IDs remain valid and are never rewritten.
- **MCP metadata + filters (A-P4):** `memory_search` / `memory_get_chunk` expose `session_date`, `path`,
  `user`, `file_hash_id`, and `related_entries`; `memory_search` filters by `user`, `date_from`, `date_to`.
- **Participant registry (S2):** `.memory-seed/project.yaml` supports a `participants:` list parsed
  fail-open and preserved across agent-selection writes.
- **Session-layout migration (A-P5):** `memory-seed migrate sessions-layout` splits legacy flat files
  into per-user files (`--dry-run`, ID-preserving, backup-before-remove, blocks ambiguous merges).
- **Schema doc:** the optional entry-level `related_entries` field is now documented in the
  `agent-rules.md` session-log schema.

### Release 2.13.0 (shipped 2026-07-01)

- **Memory Lense (in-package V1):** `memory-seed lense` serves a local FastAPI/Uvicorn browser UI
  (search, filters, timeline, graph, reader/details) backed by a rebuildable SQLite cache outside the
  repo. Install with `memory-seed[lense]`; without the extra the command prints an install hint. See
  the Pillar B note under 3.0 below for how this relates to the originally-planned separate
  distribution.
- **Related-entries generation P1:** `memory-seed link suggest`, `memory-seed link show`, and
  `build_related_entry_graph()` (bidirectional read-time traversal) are released.
- **Agent-rules lazy-skill extraction:** detailed procedures moved out of `agent-rules.md` into
  seeded skills (`history_retrieval.md`, `session_logging.md`, `end_of_turn.md`, `memory_hygiene.md`,
  `subproject_runtime.md`); `agent-rules.md` keeps startup-safe summaries and skill pointers.
- **New `agent_collaboration.md` skill** for Git-first subagent/branch/worktree/merge-conflict
  workflows.
- Packaging fix: every seeded file (ESR commands, hooks, document skills, new lazy skills) is now
  included in wheel/sdist package data.

### 3.0 - In Progress

See the reviewed, sequenced plan: [`3.0-plan.md`](3.0-plan.md).

Multi-user Phases 1-2 shipped (2.9/2.10), the core multi-user increments (A-P3 integrity validation,
A-ID 80-bit entry IDs, A-P4 MCP metadata/filters, S2 participant registry parsing, and A-P5
`migrate sessions-layout`) shipped in 2.12.0, and related-entries generation P1 shipped in 2.13.0.
Remaining work:

1. **Related-entries generation P2 (deferred, needs sign-off).** P1 (`memory-seed link suggest` +
   `memory-seed link show` + `build_related_entry_graph()`, bidirectional read-time traversal) is
   released as of 2.13.0. Scope, decisions, and the deferred P2 are in
   [`related-entries-generation-plan.md`](related-entries-generation-plan.md).
   P2: backfilling edges between two pre-existing entries, and the optional `link add` writer
   (current-entry-only) if hand-editing YAML proves painful.
2. **Pillar B separate-distribution decision (still open).** Memory Lense shipped in 2.13.0 as an
   in-package optional extra (`memory-seed[lense]`) — a **V1 delivered inside the core package**, not
   the separate distribution `3.0-plan.md` originally decided on. It already covers B1 (local
   read-only service logic), B2 (search/filter/timeline/graph/reader UI), B3 (explainability: matched
   terms/fields, lexical/semantic scores, recency multiplier), and B4 (rebuildable SQLite cache,
   outside-repo, never authoritative). What remains **undecided**: whether to still spin Pillar B out
   into its own `memory-seed-explorer` distribution as originally planned, or keep iterating on the
   in-package extra instead. Any future UI work should consume `build_related_entry_graph()` rather
   than fork graph logic.

Obsidian remains a UX inspiration or later integration, not the first implementation target.

Specs:

- [`multi-user-session-memory-proposal.md`](completed/multi-user-session-memory-proposal.md) (completed — full scope shipped through 2.12.0)
- [`multi-user-deep-research-report.md`](completed/multi-user-deep-research-report.md) (completed — recommendations fully acted on)
- [`user-interface-deep-research-report.md`](user-interface-deep-research-report.md) (still active — informed the shipped Memory Lense V1; the separate-distribution decision above remains open)

### Logic Capture Improvements - Proposed

Source: `Memory-Seed Logic Capture Improvement.md` (external review), evaluated against the current
codebase and refined through discussion. All five items below are **proposed, not yet decided or
built** — each has its own fully-specced plan doc.

1. [`git-commit-entry-linking-plan.md`](git-commit-entry-linking-plan.md) — link a decision entry to
   the commit(s) that implemented it, via a commit-message trailer convention plus an optional
   `commits:` field on the entry.
2. [`supersession-edges-plan.md`](supersession-edges-plan.md) — a typed `supersedes` edge (separate
   from `related_entries`) so a decision can mark an earlier one as replaced, plus the harmony
   contract that keeps this from inflating a superseded entry's importance score.
3. [`interaction-frequency-ranking-plan.md`](interaction-frequency-ranking-plan.md) — Option C
   (derive an importance signal from existing `related_entries` backlinks, supersession-dampened) as
   the first increment; Option B (real access-frequency telemetry folded into a second SQLite file
   alongside the existing Lense cache) as the stated end goal.
4. [`mermaid-usage-guidance-plan.md`](mermaid-usage-guidance-plan.md) — one Working Principles bullet:
   default to plain text, reserve Mermaid for spatial/temporal/concurrent structure.
5. [`failed-approaches-logging-plan.md`](failed-approaches-logging-plan.md) — one sentence in
   `session_logging.md`'s Reason Rules requiring a failed/incompatible approach to be logged under
   `A` even when not explicitly asked.

Items 1 and 2 share a discovered dependency: `links check`'s dangling-`related_entries` validation
currently only runs against per-user-day session files, not this repo's own legacy-flat layout
(verified empirically — see either plan's "Known Dependency" section). That gap should be resolved
once, shared across both.

## MCP Client Validation

- Register Memory Seed in Claude Code or another MCP-capable client:

```powershell
claude mcp add memory-seed -s user -- uvx --from memory-seed memory-seed-mcp --stdio
```

- Ask the agent a question that should require historical project memory and confirm it calls
  `memory_search` before answering.
- Record any client-specific setup differences so the README can include confirmed examples.

## Launch Assets

- Capture a real terminal screenshot or short GIF showing `memory-seed init`,
  `memory-seed-mcp-validate`, and an agent memory lookup.
- Decide whether to publish a launch note focused on solo developers, teams standardizing agent
  memory, or both.

## Ranking Experiments

- Keep ranking behavior stable on `main`.
- Run ranking experiments on a separate branch and merge only if fixture tests show a clear improvement
  without degrading current text-ranking behavior.

## Optional Semantic Dependency

- Decide whether to add an optional package extra such as `memory-seed[semantic]` for Model2Vec-backed
  embeddings.
- Keep the default CLI and MCP path dependency-light unless the optional path shows clear value.

## Community Feedback

- Watch issue reports for agent compatibility gaps across Codex, Claude Code, Gemini CLI, and other
  MCP clients.
- Use the issue templates to separate bugs, feature requests, compatibility reports, and memory
  workflow improvements.
