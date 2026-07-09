---
memory-system-version: 2.0
tags:
  - memory-seed
  - runtime-index
  - memory-seed-project
---

# Memory Seed Runtime Index

## Purpose

Memory Seed is a portable local memory system for AI coding agents. This runtime is the active control plane for developing the reusable seed, CLI, MCP memory retrieval, and compatibility behavior.

## Runtime Boundary

- Active runtime: nearest ancestor directory containing `.memory-seed/`.
- This repository root owns the root runtime.
- Nested sub-projects may define their own `.memory-seed/` directories inside their own folders.
- Legacy `.AGENTS/` remains supported by code for old projects, but this repository now uses the all-in-one `.memory-seed/` v2 layout.

## Inheritance

- Policy: inherit parent policy unless this file explicitly disables inheritance.
- Active state: local only.
- Skills: local only unless this file explicitly allows parent skill fallback.
- This root runtime has no parent runtime.

## Always Read

1. `AGENTS.md`
2. `.memory-seed/agent-rules.md`
3. `.memory-seed/index.md`
4. `.memory-seed/policy.md`
5. `.memory-seed/skills/index.md`

## Lazy Skills

Use `.memory-seed/skills/index.md` as the deterministic trigger registry. Load the full skill runbooks below only when the registry matches the task:

- `.memory-seed/skills/security_triage.md`
- `.memory-seed/skills/agent_collaboration.md`
- `.memory-seed/skills/history_retrieval.md`
- `.memory-seed/skills/session_logging.md`
- `.memory-seed/skills/compact_mermaid_diagrams.md`
- `.memory-seed/skills/end_of_turn.md`
- `.memory-seed/skills/memory_hygiene.md`
- `.memory-seed/skills/risk_signaling.md`
- `.memory-seed/skills/skill_architecture.md`
- `.memory-seed/skills/proposal_lifecycle.md`
- `.memory-seed/skills/subproject_runtime.md`
- `.memory-seed/skills/data_architecture.md`
- `.memory-seed/skills/local_compilation.md`
- `.memory-seed/skills/code_search.md`
- `.memory-seed/skills/memory_consolidation.md`
- `.memory-seed/skills/memory_doctor.md`
- `.memory-seed/skills/release_publishing.md`
- `.memory-seed/skills/document_ingestion.md`
- `.memory-seed/skills/office_document_editing.md`

## Active State

- Project type: reusable local AI memory-system seed and Python CLI/MCP tooling.
- Current priority: use this repository as a meta-test for the all-in-one `.memory-seed/` v2 layout with nearest-runtime sub-project discovery.
- Main output: plain-file local memory system for AI agents plus Python package `memory-seed`.
- Current risk: private/local system design work with possible personal notes because this project lives inside a second-brain folder.
- Current risk: subagents or isolated worktrees spawned for this repo can silently inherit a stale git worktree pinned to an old commit rather than the live tree, producing fabricated or outdated citations if untrusted.
- Control-plane version: `2.16`.
- Package version: `2.16.0`.

## Topology

- Root routing files: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` (Copilot thin router).
- Runtime files: `.memory-seed/agent-rules.md`, `.memory-seed/project-bootstrap.md`, bootstrap-generated `.memory-seed/index.md`, bootstrap-generated `.memory-seed/policy.md`, init-managed `.memory-seed/project.yaml` (agent, skill, and participant selection), `.memory-seed/skills/`, `.memory-seed/sessions/`, `.memory-seed/archive/`, `.memory-seed/hooks/`.
- Lifecycle hooks (`.memory-seed/hooks/`): `session-log-check.py` (turn-end log reminder), `memory-retrieval-check.py` (per-prompt topical-retrieval reminder), `session-start-context.py` (SessionStart — injects the newest session entries so agents establish current state by recency, not semantic search). Per-agent events differ: Claude `Stop`/`UserPromptSubmit`/`SessionStart`; Codex same; Gemini `AfterAgent`/`BeforeAgent`/`SessionStart` (it has no `Stop`/`UserPromptSubmit`); Cursor `afterAgentResponse`/`sessionStart`.
- Agent hook configs (auto-merged by `init`/`update`): `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json`, `.cursor/hooks.json`, plus Copilot CLI `.github/hooks/memory-seed.json` (sessionStart prompt hook).
- Agent MCP configs (auto-registered by `init`/`update`): `.mcp.json` (Claude Code, project root), `.cursor/mcp.json` (Cursor), `.gemini/settings.json` (Gemini), `.codex/config.toml` (Codex, trusted directories only), `.github/mcp.json` (Copilot CLI, `mcpServers` key), `.vscode/mcp.json` (VS Code Copilot, `servers` key).
- Legacy `.AGENTS/`: supported by code for old projects, but not part of the v2 target shape.
- Python orchestration: `memory_seed/core.py`, `memory_seed/semantic_cache.py`, `memory_seed/mcp_server.py`, `memory_seed/mcp_validate.py`, `memory_seed/cli.py`, `memory_seed/retrieval.py` (the public retrieval service the UI consumes).
- Companion review UI (separate distribution): `memory-trace/` — the `memory-trace` package/command (formerly the in-package Memory Lense). Depends on `memory-seed`, consumes `memory_seed/retrieval.py`, and owns the web stack (`fastapi`/`uvicorn`) + static assets (`memory-trace/memory_trace/static/`). Core ships no web framework; `memory-seed lense` is a deprecation shim pointing here.
- Seed templates: `memory_seed/seed/`.
- Tests: `tests/`.
- Public docs: `README.md`, `CHANGELOG.md`, `docs/2_Todo/0_NEXT_STEPS.md`.
- Docs taxonomy: `docs/1_Inbox/` holds unassessed incoming material; `docs/2_Todo/` holds open memory-seed roadmap proposals; `docs/2_Todo/completed/` holds proposals that shipped or were otherwise resolved, plus the standalone persona-template asset (`docs/2_Todo/completed/agent-templates/`); `docs/4_Reference/` holds source research and reference material that informs proposals but is not itself an actionable proposal; `docs/3_Spec/` holds live normative specs such as the functionality audit and graph-edge contract; `docs/2_Todo/codex/` and `docs/2_Todo/Claude/` hold per-agent synthesis/evaluation reports.
- **Sub-project: `demo/`** — HyperFrames video composition (30 s product demo, MP4). Has its own `.memory-seed/` runtime; inherits root policy. HyperFrames owns `demo/AGENTS.md` and `demo/CLAUDE.md`; each now carries an injected `<!-- BEGIN memory-seed -->` routing block (2.8) so agents are routed into the demo runtime without clobbering HyperFrames content.

## Design Decisions

- `.memory-seed/` is the canonical runtime directory.
- Runtime discovery walks upward from `cwd` and uses the nearest `.memory-seed/`.
- `.memory-seed/agent-rules.md` and `.memory-seed/project-bootstrap.md` are reusable procedure files inside the runtime.
- `memory-seed init` installs reusable control files, generic skill templates, and lifecycle hooks; it does not create generated project memory files.
- `.claude/settings.json` and `.codex/hooks.json` are handled as JSON merge targets during init/update — not seed file copies — so existing agent config is preserved.
- `session-log-check.py` accepts `--codex` flag: outputs `hookSpecificOutput.additionalContext` for Claude, `systemMessage` for Codex.
- Bootstrap generates `index.md`, `policy.md`, and the first dated session log after inspecting the project and asking targeted user questions.
- Sub-projects live as normal folders with their own `.memory-seed/`; they are not nested inside the root `.memory-seed/`.
- Parent policy and skills are inherited by default for sub-projects unless the sub-project index records a local override; local skills should only duplicate parent skills when overriding behavior or defining genuinely local runbooks.
- `index.md` combines topology, active state, durable project context, current priorities, workflows, risks, inheritance, and skill activation.
- `policy.md` contains behavioral constraints only.
- `.memory-seed/skills/index.md` is the deterministic trigger registry for deciding which lazy-loaded skills apply.
- `skills/*.md` are lazy-loaded execution runbooks.
- `.memory-seed/sessions/` is the rationale and audit trail for decisions; `index.md` should store current orientation and durable conclusions, not full decision history.
- `memory-seed update` archives replaced reusable control-plane files under `.memory-seed/archive/<old-version>/` or `.memory-seed/archive/unknown-<timestamp>/` before refreshing them.
- MCP memory search uses the Model2Vec static embedding provider `model2vec:minishlab/potion-base-8M` by default and falls back to lexical, metadata, and recency ranking if semantic scoring fails or is disabled.
- Claude Code reads project-scope MCP servers from a project-root `.mcp.json`, NOT from `.claude/settings.json > mcpServers` (silently ignored). Versions 2.2.0–2.3.0 mis-wrote it to settings.json; `update` now writes `.mcp.json` and strips the dead block (ours-only).
- Codex reads project MCP from `.codex/config.toml` (`[mcp_servers.<name>]`, trusted directories only). Auto-registered via a zero-dependency TOML text-upsert (stdlib `tomllib` inspects; line-based writes preserve comments). A stale entry in a non-standard TOML form is left as a safe no-op.
- `doctor` has a non-fatal `warnings` channel (`DoctorResult.warnings`). It classifies the Codex MCP entry as absent/current/foreign/stale-fixable/stale-manual so an un-migratable stale entry is surfaced for manual fix rather than silently ignored.
- The single-decision DRAFT record is the **baseline** session-entry shape (since 2.4.0); the bare summary (simpler) and multi-decision (richer) shapes are explicit routes off it. D/R are mandatory, A/F/T optional.
- Release/publish: creating a GitHub Release triggers `.github/workflows/publish.yml`; the `pypi` environment has a **manual-approval gate** (a required reviewer must approve the deployment) before the OIDC PyPI push. The build job runs `tests.test_memory_seed`, so those tests must be clock-robust.
- Orphan/dead-artifact review (2.7.0): the End Of Turn routine (`agent-rules.md` + seed twin, mirrored in `.claude/commands/esr.md`) gained a diff-scoped **orphan & artifact sweep** — confirm new files/features are wired in, grep for references left dangling by deletions/renames, flag scratch debris; an optional declared dead-code tool (vulture/ruff, knip, ArchUnit, cppcheck) may be run but is never installed. The sweep catches orphan *files/features*; whole-codebase *dead code* stays a periodic tool job. Backstopped by a deterministic `doctor` warning: any `.memory-seed/skills/*.md` not registered in `skills/index.md` is flagged as an orphan skill.
- Non-destructive routing into foreign entry-point files (2.8.0): the four routing files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, set `ROUTING_DESTINATIONS` in `core.py`) follow a 4-way ownership branch in `init`/`update`: greenfield → write full seed file; ours (has `memory-system-version` frontmatter) → version-gated archive+replace; foreign with our markers → re-sync the managed block in place; foreign without markers → inject a marker-delimited routing block (`_merge_routing_stanza`, mirrors `_merge_grouped_hook`). A foreign file is **never overwritten** — even under `init --force`. The "second merge" on a version bump replaces only the block, gated on content-equality (no churn when stanza text is unchanged). **Behavior change:** a versionless entry-point file is now merged, not overwritten (retired the legacy unversioned→clobber path). Backstopped by a `doctor` warning: a `.memory-seed/` runtime with a present-but-foreign-without-block entry-point file is flagged as an orphaned runtime.
- Multi-user session dual-read discovery (2.9.0): package readers use `iter_session_documents()` in `core.py` to read both legacy flat session files (`sessions/YYYY-MM-DD.md`) and per-day/per-user files (`sessions/YYYY-MM-DD/<user>.md`, bare slug such as `jean.md`). `extract_memory_chunks()`/MCP and `compact_sessions()` discover both layouts; fallback chunk IDs use date-qualified source paths.
- Session-memory integrity validation (2.12.0, multi-user Phase 3): `check_session_links()` in `core.py` validates both layouts (duplicate `entry_id`/`hash_id`, dangling `related_entries`/`related_memories`, per-user frontmatter user/date/schema_version/hash_id problems) using `iter_session_documents`; surfaced as `memory-seed links check` (non-zero exit = CI gate) with a one-line `doctor` summary. Stdlib-only frontmatter scan (`_parse_frontmatter_scalars`/`_frontmatter_list_region`); first increment of the reviewed 3.0 plan (`docs/2_Todo/3.0-plan.md`).
- Entry-ID widening + MCP metadata filters (current unreleased worktree): new generated session `entry_id` values use deterministic 80-bit `mse_` IDs while legacy `ms-` IDs remain valid and are never rewritten. `memory_search`/`memory_get_chunk` expose `session_date`, `path`, per-user `user`, `file_hash_id`, and entry-level `related_entries`; `memory_search` filters by `user`, `date_from`, and `date_to` before ranking.
- Participant registry parsing (current unreleased worktree): `.memory-seed/project.yaml` supports a `participants:` list alongside existing `agents:` selection. `read_project_participants()` parses valid `slug`/`initials`/`display_name` entries fail-open, and `write_project_agents()` preserves the participants block. `session_target()` gates per-user layout on participant count: a configured local user alone is not enough — per-user files (`sessions/YYYY-MM-DD/<user>.md`) only activate once 2+ participants are registered; an explicit `--user` override bypasses the gate. `doctor` warns when the active local user isn't among the registered participants.
- Identity-offer nudge (current unreleased worktree): `session-start-context.py` offers one-time setup guidance when no identity is configured at all (no `MEMORY_SEED_USER`, no `local.yaml`); tracked via a gitignored `.memory-seed/.identity-offer-stamp` so it asks once per project, never repeats per session.
- Session-layout migration (current unreleased worktree): `memory-seed migrate sessions-layout` splits legacy flat `sessions/YYYY-MM-DD.md` files into per-user `sessions/YYYY-MM-DD/<user>.md` files by mapping entry `user_initials` through `.memory-seed/project.yaml` participants. It supports `--dry-run`, preserves entry IDs, creates one per-user file `hash_id`, backs up migrated flat files, removes migrated sources to avoid dual-read duplicate IDs, and blocks ambiguous or unsafe merges.
- Related-entries generation P1 (current unreleased worktree): `build_related_entry_graph()` in `semantic_cache.py` builds the bidirectional related-entry graph (stored outbound edges + inbound backlinks computed only from resolvable refs; accepts a pre-extracted `chunks=` corpus to avoid re-parsing). Exposed read-only via `memory-seed link suggest` (ranks **older** candidate entries to link, reuses `rank_memory_chunks`, prints a paste-ready snippet) and `memory-seed link show <entry_id>` (outbound + inbound backlinks). Forward-only authoring + read-time bidirectional traversal preserves append-only; backfill between pre-existing entries and an optional `link add` writer are deferred (P2). Scope/decisions in `docs/2_Todo/completed/related-entries-generation-plan.md`.
- Risk signaling skill (current unreleased worktree): `.memory-seed/skills/risk_signaling.md` adds qualitative Proceed / Proceed-and-flag / Propose-and-wait / Stop tiers and STOP categories for destructive, irreversible, security/trust-boundary, shared/control-plane, external-communication, and financial actions. Registered in the live and seeded trigger registries; cross-referenced from collaboration and security triage.
- Encoding hardening (current unreleased worktree): `memory-seed encoding check` reports UTF-8/BOM/newline/NFC drift, likely mojibake, and implicit production Python text I/O; `encoding repair` previews or atomically repairs mechanically safe BOM/newline/NFC drift after timestamped backup. Invalid UTF-8 and likely mojibake remain manual. Encoding policy stays owned by Memory Seed rather than being duplicated in Memory Trace, and `doctor` provides a non-fatal summary.
- Memory Trace UI (current unreleased worktree): the human review UI has moved to the standalone `memory-trace` package/command. The old `memory-seed lense` route is a deprecated compatibility shim. Markdown session files remain the source of truth; Trace exposes searchable memory, filters, timeline, graph, Trail, reader/details, pane resizing, light/dark themes, accent palettes, entry-level results with section highlights, and client-side Mermaid sidecar rendering through paged APIs.
- ESR generalization (2.11.0): the "End Of Turn" routine in `agent-rules.md` (+ seed twin) now runs a consolidation review (promote durable facts → `index.md`/`policy.md` via `memory_consolidation`) and a baseline-promotion check (flag generic adaptations, record in `.memory-seed/plans/`, create-if-needed). Shipped as a seeded `/esr` command via two `SeedFile`s: `.claude/commands/esr.md` (agent=claude, version-tracked frontmatter, refreshes on update) and `.gemini/commands/esr.toml` (agent=gemini, deploy-once via `_is_runtime_local_file` since TOML carries no version marker). Codex/Cursor run the routine from `agent-rules.md`. No blocking `Stop` hook (deliberate — evolution needs reasoning + approval).
- User-aware session targets (2.10.0): user identity is opt-in and local-first. Resolution order is explicit CLI/function argument, `MEMORY_SEED_USER`, gitignored `.memory-seed/local.yaml`, then legacy flat-file behavior. `session_target()` returns `sessions/YYYY-MM-DD.md` when no user is configured and `sessions/YYYY-MM-DD/<user>.md` when a valid slug is active; `--create` initializes per-user file frontmatter with `schema_version: 2`, `session_date`, immutable `msm_` file `hash_id`, `user`, and `created_at`. Hooks are user-aware: `session-log-check.py` checks only the active user's file, while `session-start-context.py` injects the active user's latest entry and lists same-day co-contributor files by count.
- Agent-selective install (2.6.0 plus current unreleased UX refinement): `init` installs only the chosen agents' files; the set is persisted in `.memory-seed/project.yaml` (`agents:` list) and respected by `doctor`/`update`. Interactive init now presents agent integrations as an opt-out step with all agents selected by default; `--agents none` writes the explicit zero-agent state and `--no-agent-prompt` skips the prompt. Driven by the `KNOWN_AGENTS`/`_AGENT_MERGES`/`_AGENT_UNINSTALLS` registries in `core.py` and a per-`SeedFile` `agent` tag. Absent `project.yaml` means all agents for legacy projects; present-but-empty `agents:` means zero agents. `agents list` reports selected and ignored agents. `agents add/remove` reconfigure; `remove` strips only our entries (foreign config preserved), never deletes shared dirs, backs up first. `codex`/`cursor` have no routing file (read `AGENTS.md` natively).

## Session Memory

- Append meaningful work notes to the active session target (`memory-seed session target`), which is legacy flat (`.memory-seed/sessions/YYYY-MM-DD.md`) unless a local user is configured.
- Keep session entries concise, publishable, and free of secrets.
- Older `.AGENTS/sessions/` logs were migrated into `.memory-seed/sessions/` for the v2 meta-test.
