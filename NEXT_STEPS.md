# Next Steps

These items need user judgement, account access, or real-client validation.

## Active Roadmap

Approved 2026-06-13. Incremental release: 2.6.0 now, 2.7.0 later. Source: docs/todo review + the SessionStart-hardening session findings.

### Release 2.6.0 (shipped 2026-06-13)

Bundles the already-built-but-uncommitted SessionStart orientation hook (Claude/Codex/Gemini/Cursor) and Copilot CLI support, plus:

- **Gemini dead-wiring fix (bug):** the repo wires Gemini hooks to `Stop`/`UserPromptSubmit`, which Gemini does not expose. Correct events are `AfterAgent` (turn-end) and `BeforeAgent` (prompt-submit); `SessionStart` is already correct. Strip the dead entries on `update` and align the `--gemini` hook output to `hookSpecificOutput.additionalContext`.
- **Copilot VS Code surface:** `.vscode/mcp.json` (uses the `servers` key, not `mcpServers`) + a thin `.github/copilot-instructions.md` router. Document the coding-agent MCP path (repo/org settings, manual). Reconcile docs/todo item 5.
- **Hygiene:** fix `index.md` Active State version staleness; trim over-specified doc-substring tests + repoint the frozen-file test; reconcile the per-prompt `memory-retrieval-check.py` wording with the recency-vs-topical rule.
- **Release mechanics:** version bump 2.5â†’2.6 / 2.5.0â†’2.6.0 (incl. repo-root files + index Active State â€” the version-bump trap), CHANGELOG, README agent list, demo refresh, archive 2.5 snapshot, publish.

### Release 2.7.0 (shipped 2026-06-14)

- **Orphan & dead-artifact review (done):** diff-scoped orphan/artifact sweep added to the "End Of Turn" routine in `agent-rules.md` (+ seed twin, mirrored in `/esr`); deterministic orphan-skill warning added to `doctor` (any `skills/*.md` not registered in `skills/index.md`). Language-agnostic, never installs tools; whole-codebase dead code stays a periodic tool job.
- **Seed promotions (done):** `document_ingestion` and `office_document_editing` skills ported into the seed + live runtime with trigger-registry entries; "Working Principles" block (POC-gate / verification-split / share-aware) added to `agent-rules.md`.
- **ESR generalization** (not started): add consolidationâ†’index/policy and baseline-promotion steps to `/esr`, and ship it as a vendor-neutral seeded command (today it is Claude-only). No blocking `Stop` nudge hook.

### Release 2.8.0 (shipped 2026-06-14)

- **Non-destructive routing into foreign entry-point files (done):** the four routing files (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`.github/copilot-instructions.md`) follow a 4-way ownership branch in `init`/`update` â€” greenfield full-file; owned (frontmatter) â†’ version-gated archive+replace; foreign-with-markers â†’ in-place block re-sync; foreign-without â†’ inject a marker-delimited routing block. A foreign file is never overwritten (even under `--force`); the "second merge" on a version bump is content-equality-gated (no churn). Resolves the demo collision: a project where another tool (HyperFrames) owns `AGENTS.md`/`CLAUDE.md` now routes into the `.memory-seed/` runtime without losing host content.
- **Behavior change (done):** versionless entry-point files are merged, not overwritten â€” retires the legacy unversionedâ†’clobber upgrade path.
- **Doctor route-presence backstop (done):** a `.memory-seed/` runtime whose present entry-point file is foreign-without-block is flagged as orphaned.

### Release 2.9.0 (shipped 2026-06-14)

- **Multi-user session dual-read discovery (done):** package readers now discover both legacy flat files (`.memory-seed/sessions/YYYY-MM-DD.md`) and per-day/per-user files (`.memory-seed/sessions/YYYY-MM-DD/<user>.md`). This is read-only groundwork for multi-user attribution and Git-merge avoidance.

### Release 2.10.0 (in progress)

- **User-aware session targets (done in code):** local user identity is opt-in through `.memory-seed/local.yaml`, `MEMORY_SEED_USER`, or `memory-seed session target --user`. `memory-seed session target --create` initializes `.memory-seed/sessions/YYYY-MM-DD/<user>.md` with file frontmatter and an immutable `msm_` hash. With no configured user, legacy flat-file targets remain unchanged.
- **User-aware hooks (done in code):** `session-log-check.py` checks only the active user's file, and `session-start-context.py` injects the active user's newest entry plus same-day co-contributor file counts.

### Deferred â€” 3.0 candidate

- **Multi-user per-day session memory remaining phases** (`.memory-seed/sessions/YYYY-MM-DD/<user>.md`). Team-capable direction (attribution + Git-merge avoidance; not privacy/permissions/real-time). Phase 1 dual-read discovery landed in 2.9.0 and Phase 2 user-aware targets/hooks landed in 2.10.0; still deferred are graph-link validation, MCP metadata filters, explicit `migrate sessions-layout`, and any future entry-ID widening. Refined execution-ready spec: [`docs/todo/multi-user-session-memory-proposal.md`](docs/todo/multi-user-session-memory-proposal.md); design rationale in [`docs/todo/multi-user-deep-research-report.md`](docs/todo/multi-user-deep-research-report.md).

## MCP Client Validation

- Register Memory Seed in Claude Code or another MCP-capable client:

```powershell
claude mcp add memory-seed -s user -- uvx --from memory-seed memory-seed-mcp --stdio
```

- Ask the agent a question that should require historical project memory and confirm it calls `memory_search` before answering.
- Record any client-specific setup differences so the README can include confirmed examples.

## Launch Assets

- Capture a real terminal screenshot or short GIF showing `memory-seed init`, `memory-seed-mcp-validate`, and an agent memory lookup.
- Decide whether to publish a launch note focused on solo developers, teams standardizing agent memory, or both.

## Ranking Experiments

- Keep ranking behavior stable on `main`.
- Run ranking experiments on a separate branch and merge only if fixture tests show a clear improvement without degrading current text-ranking behavior.

## Optional Semantic Dependency

- Decide whether to add an optional package extra such as `memory-seed[semantic]` for Model2Vec-backed embeddings.
- Keep the default CLI and MCP path dependency-light unless the optional path shows clear value.

## Community Feedback

- Watch issue reports for agent compatibility gaps across Codex, Claude Code, Gemini CLI, and other MCP clients.
- Use the issue templates to separate bugs, feature requests, compatibility reports, and memory workflow improvements.
