# Next Steps

These items need user judgement, account access, or real-client validation.

## Active Roadmap

Approved 2026-06-13. Incremental release: 2.6.0 now, 2.7.0 later. Source: docs/todo review + the SessionStart-hardening session findings.

### Release 2.6.0 (in progress)

Bundles the already-built-but-uncommitted SessionStart orientation hook (Claude/Codex/Gemini/Cursor) and Copilot CLI support, plus:

- **Gemini dead-wiring fix (bug):** the repo wires Gemini hooks to `Stop`/`UserPromptSubmit`, which Gemini does not expose. Correct events are `AfterAgent` (turn-end) and `BeforeAgent` (prompt-submit); `SessionStart` is already correct. Strip the dead entries on `update` and align the `--gemini` hook output to `hookSpecificOutput.additionalContext`.
- **Copilot VS Code surface:** `.vscode/mcp.json` (uses the `servers` key, not `mcpServers`) + a thin `.github/copilot-instructions.md` router. Document the coding-agent MCP path (repo/org settings, manual). Reconcile docs/todo item 5.
- **Hygiene:** fix `index.md` Active State version staleness; trim over-specified doc-substring tests + repoint the frozen-file test; reconcile the per-prompt `memory-retrieval-check.py` wording with the recency-vs-topical rule.
- **Release mechanics:** version bump 2.5→2.6 / 2.5.0→2.6.0 (incl. repo-root files + index Active State — the version-bump trap), CHANGELOG, README agent list, demo refresh, archive 2.5 snapshot, publish.

### Release 2.7.0 (specified, not started)

- **Seed promotions** (from docs/todo): `document_ingestion` skill, `office_document_editing` skill, and the "Working Principles" block (POC-gate / verification-split / share-aware) into `agent-rules.md`.
- **ESR generalization:** add consolidation→index/policy and baseline-promotion steps to `/esr`, and ship it as a vendor-neutral seeded command (today it is Claude-only). No blocking `Stop` nudge hook.

### Deferred — 3.0 candidate

- **Multi-user per-day session memory** (`.memory-seed/sessions/YYYY-MM-DD/<user>.memory.md`). Team-capable direction (attribution + Git-merge avoidance; not privacy/permissions/real-time). Dual-read compatible, opt-in writes, explicit `migrate sessions-layout`. Refined execution-ready spec: [`docs/todo/multi-user-session-memory-proposal.md`](docs/todo/multi-user-session-memory-proposal.md); design rationale in [`docs/todo/multi-user-deep-research-report.md`](docs/todo/multi-user-deep-research-report.md). **Do not start** until 2.6.0 ships and 2.7.0 lands — it changes the core session data model (high blast radius) and warrants a deliberate product decision.

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
