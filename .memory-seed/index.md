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
- Goal run 2026-07-10 COMPLETE: all four phases of `docs/2_Todo/completed/goal-roadmap-refinement-and-staged-implementation.md` executed; v2.17.0 released; Memory Trace packaging now ships through the root `memory-seed[trace]` extra with the `memory-trace` command.
- Long-horizon Wave 1 shipped 2026-07-15: deterministic topic suggestions, timeline Evidence Pack Phase 1, Trail continuity lanes, `superseding_head` plus the full-corpus-gated successor boost, configurable integration mode through all four phases, and inert lifecycle-link scaffold steps 1–3. The four complete plans live in `docs/5_Completed/`; AI summarisation remains active for provider/local-model Phase 2 and lifecycle-link authoring remains active for evaluation with optional steps 4–5 deferred.
- Memory Trace next-generation planning promoted 2026-07-11: `docs/2_Todo/memory-trace-product-and-system-architecture-blueprint.md` is the top-level plan, `docs/2_Todo/memory-trace-next-generation-implementation-roadmap.md` sequences future work, and `docs/2_Todo/memory-trace-next-generation-coverage-matrix.md` preserves which older implementation plans remain active. B0a graph/workspace contracts and renderer evidence completed 2026-07-16; Cytoscape.js 3.34.0 is selected. B0b now packages the React/TypeScript `/next` shell with the accepted vanilla graph, search, selection, and workspace interaction rules, while vanilla `/` remains the fallback. Remaining B0b acceptance work is renderer-neutral React diagram rendering, actual topology-community and temporal layout, accessibility, and residual Trail parity; the stated 2.19 memory-quality cut criterion is met, but release/publish still requires explicit user approval.
- Inbox triage completed 2026-07-16 under Constitution v1.1. After B0b plus the provenance/quality gates,
  `docs/2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md` leads the semantic program with
  authoritative append-only Markdown ADR sidecars; workflow evidence/review and one Decision projection
  follow. Publishability and a generic skill/workflow router remain deferred. The worktree hygiene plan uses
  worktree=session, branch=task, and `<agent>/<kind>/<topic>` for new branches.
- Main output: plain-file local memory system for AI agents plus Python package `memory-seed`.
- Current risk: private/local system design work with possible personal notes because this project lives inside a second-brain folder.
- Current risk: subagents or isolated worktrees spawned for this repo can silently inherit a stale git worktree pinned to an old commit rather than the live tree, producing fabricated or outdated citations if untrusted.
- Control-plane version: `2.18`.
- Package version: `2.18.0`.

## Topology

- Root routing files: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` (Copilot thin router).
- Runtime files: `.memory-seed/agent-rules.md`, `.memory-seed/project-bootstrap.md`, bootstrap-generated `.memory-seed/index.md`, bootstrap-generated `.memory-seed/policy.md`, init-managed `.memory-seed/project.yaml` (agent, skill, and participant selection), `.memory-seed/skills/`, `.memory-seed/sessions/`, `.memory-seed/archive/`, `.memory-seed/hooks/`.
- Lifecycle hooks (`.memory-seed/hooks/`): `session-log-check.py` (turn-end log reminder), `memory-retrieval-check.py` (per-prompt topical-retrieval reminder), `session-start-context.py` (SessionStart — injects the newest session entries so agents establish current state by recency, not semantic search), `prepare-commit-msg.py` (a **git** hook, not an agent hook: auto-stamps `Memory-Entry:` trailers for staged session entries; shim installed into the git common dir by `init` / `memory-seed hooks install`, never blocks a commit). Per-agent events differ: Claude `Stop`/`UserPromptSubmit`/`SessionStart`; Codex same; Gemini `AfterAgent`/`BeforeAgent`/`SessionStart` (it has no `Stop`/`UserPromptSubmit`); Cursor `afterAgentResponse`/`sessionStart`.
- Agent hook configs (auto-merged by `init`/`update`): `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json`, `.cursor/hooks.json`, plus Copilot CLI `.github/hooks/memory-seed.json` (sessionStart prompt hook).
- Agent MCP configs (auto-registered by `init`/`update`): `.mcp.json` (Claude Code, project root), `.cursor/mcp.json` (Cursor), `.gemini/settings.json` (Gemini), `.codex/config.toml` (Codex, trusted directories only), `.github/mcp.json` (Copilot CLI, `mcpServers` key), `.vscode/mcp.json` (VS Code Copilot, `servers` key).
- Legacy `.AGENTS/`: supported by code for old projects, but not part of the v2 target shape.
- Python orchestration: `memory_seed/core.py`, `memory_seed/semantic_cache.py`, `memory_seed/mcp_server.py`, `memory_seed/mcp_validate.py`, `memory_seed/cli.py`, `memory_seed/retrieval.py` (the public retrieval service the UI consumes).
- Companion review UI (Trace source / optional extra target): `memory-trace/` is the `memory_trace` UI source package and owns the `memory-trace` command (formerly the in-package Memory Lense). It consumes `memory_seed/retrieval.py` and owns the web stack (`fastapi`/`uvicorn`) + static assets (`memory-trace/memory_trace/static/`). The release strategy now folds Trace into the root `memory-seed[trace]` install path rather than a separate PyPI project; plain `memory-seed` must still ship no web framework, and `memory-seed lense` remains a deprecated shim/alias path.
- Seed templates: `memory_seed/seed/`.
- Tests: `tests/`.
- Public docs: `README.md`, `CHANGELOG.md`, `docs/2_Todo/0_NEXT_STEPS.md`.
- Docs taxonomy: `docs/1_Inbox/` holds unassessed incoming material; `docs/2_Todo/` holds active roadmap proposals; `docs/3_Spec/` holds live normative specs (with candidates in `draft/`); `docs/4_Reference/` holds source research; and terminal outcomes live in `docs/5_Completed/`, `6_Rejected/`, `7_Superseded/`, or `8_Deferred/`. The legacy `docs/2_Todo/completed/` archive was retired 2026-07-17: its 43 documents and nested `agent-templates/` moved to `docs/5_Completed/`, so every terminal doc now sits in a lane.
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
- Authoritative memory may be partitioned across append-only Markdown entries and narrowly scoped Markdown
  sidecars. Under the adopted but not-yet-implemented ADR contract, the sidecar will own promotion and
  lifecycle while entries own rationale/evidence; current status, registries, indexes, databases, and Trace
  views are derived.
- `memory-seed update` archives replaced reusable control-plane files under `.memory-seed/archive/<old-version>/` or `.memory-seed/archive/unknown-<timestamp>/` before refreshing them.
- MCP memory search uses the Model2Vec static embedding provider `model2vec:minishlab/potion-base-8M` by default and falls back to lexical, metadata, and recency ranking if semantic scoring fails or is disabled.
- Claude Code reads project-scope MCP servers from a project-root `.mcp.json`, NOT from `.claude/settings.json > mcpServers` (silently ignored). Versions 2.2.0–2.3.0 mis-wrote it to settings.json; `update` now writes `.mcp.json` and strips the dead block (ours-only).
- Codex reads project MCP from `.codex/config.toml` (`[mcp_servers.<name>]`, trusted directories only). Auto-registered via a zero-dependency TOML text-upsert (stdlib `tomllib` inspects; line-based writes preserve comments). A stale entry in a non-standard TOML form is left as a safe no-op.
- `doctor` has a non-fatal `warnings` channel (`DoctorResult.warnings`). It classifies the Codex MCP entry as absent/current/foreign/stale-fixable/stale-manual so an un-migratable stale entry is surfaced for manual fix rather than silently ignored.
- The single-decision DRAFT record is the **baseline** session-entry shape (since 2.4.0); the bare summary (simpler) and multi-decision (richer) shapes are explicit routes off it. D/R are mandatory, A/F/T optional.
- Release/publish: creating a GitHub Release triggers `.github/workflows/publish.yml`; the `pypi` environment has a **manual-approval gate** (a required reviewer must approve the deployment) before the OIDC PyPI push. The build job runs `tests.test_memory_seed`, so those tests must be clock-robust.
- Orphan/dead-artifact review (2.7.0): the End Of Turn routine (`agent-rules.md` + seed twin, mirrored in `.claude/commands/esr.md`) gained a diff-scoped **orphan & artifact sweep** — confirm new files/features are wired in, grep for references left dangling by deletions/renames, flag scratch debris; an optional declared dead-code tool (vulture/ruff, knip, ArchUnit, cppcheck) may be run but is never installed. The sweep catches orphan *files/features*; whole-codebase *dead code* stays a periodic tool job. Backstopped by a deterministic `doctor` warning: any `.memory-seed/skills/*.md` not registered in `skills/index.md` is flagged as an orphan skill.
- Non-destructive routing into foreign entry-point files (2.8.0): the four routing files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, set `ROUTING_DESTINATIONS` in `core.py`) follow a 4-way ownership branch in `init`/`update`: greenfield → write full seed file; ours (has `memory-system-version` frontmatter) → version-gated archive+replace; foreign with our markers → re-sync the managed block in place; foreign without markers → inject a marker-delimited routing block (`_merge_routing_stanza`, mirrors `_merge_grouped_hook`). A foreign file is **never overwritten** — even under `init --force`. The "second merge" on a version bump replaces only the block, gated on content-equality (no churn when stanza text is unchanged). **Behavior change:** a versionless entry-point file is now merged, not overwritten (retired the legacy unversioned→clobber path). Backstopped by a `doctor` warning: a `.memory-seed/` runtime with a present-but-foreign-without-block entry-point file is flagged as an orphaned runtime.
- Session document discovery: package readers use `iter_session_documents()` in `core.py` to read legacy flat session files (`sessions/YYYY-MM-DD.md`), legacy per-day/per-user files (`sessions/YYYY-MM-DD/<user>.md`), new month-grouped flat files (`sessions/YYYY-MM/YYYY-MM-DD.md`), and new month-grouped per-user files (`sessions/YYYY-MM/YYYY-MM-DD/<user>.md`). `extract_memory_chunks()`/MCP, Memory Trace, hooks, `links check`, and `compact_sessions()` discover the supported layouts; fallback chunk IDs use date-qualified source paths.
- Session-memory integrity validation (2.12.0, multi-user Phase 3): `check_session_links()` in `core.py` validates both layouts (duplicate `entry_id`/`hash_id`, dangling `related_entries`/`related_memories`, per-user frontmatter user/date/schema_version/hash_id problems) using `iter_session_documents`; surfaced as `memory-seed links check` (non-zero exit = CI gate) with a one-line `doctor` summary. Stdlib-only frontmatter scan (`_parse_frontmatter_scalars`/`_frontmatter_list_region`); first increment of the reviewed 3.0 plan (`docs/2_Todo/3.0-plan.md`).
- Entry-ID widening + MCP metadata filters (shipped 2.12.0): new generated session `entry_id` values use deterministic 80-bit `mse_` IDs while legacy `ms-` IDs remain valid and are never rewritten. `memory_search`/`memory_get_chunk` expose `session_date`, `path`, per-user `user`, `file_hash_id`, and entry-level `related_entries`; `memory_search` filters by `user`, `date_from`, and `date_to` before ranking.
- Participant registry parsing (registry shipped 2.12.0; participant-count gating 2.14.0): `.memory-seed/project.yaml` supports a `participants:` list alongside existing `agents:` selection. `read_project_participants()` parses valid `slug`/`initials`/`display_name` entries fail-open, and `write_project_agents()` preserves the participants block. `session_target()` gates per-user layout on participant count: a configured local user alone is not enough — per-user files (`sessions/YYYY-MM/YYYY-MM-DD/<user>.md`) only activate once 2+ participants are registered; an explicit `--user` override bypasses the gate. `doctor` warns when the active local user isn't among the registered participants.
- Identity-offer nudge (shipped 2.14.0): `session-start-context.py` offers one-time setup guidance when no identity is configured at all (no `MEMORY_SEED_USER`, no `local.yaml`); tracked via a gitignored `.memory-seed/.identity-offer-stamp` so it asks once per project, never repeats per session.
- Session-layout migration (sessions-layout shipped 2.12.0; sessions-month-layout current unreleased worktree): `memory-seed migrate sessions-layout` splits legacy flat `sessions/YYYY-MM-DD.md` files into per-user `sessions/YYYY-MM/YYYY-MM-DD/<user>.md` files by mapping entry `user_initials` through `.memory-seed/project.yaml` participants. It supports `--dry-run`, preserves entry IDs, creates one per-user file `hash_id`, backs up migrated flat files, removes migrated sources to avoid dual-read duplicate IDs, and blocks ambiguous or unsafe merges. `memory-seed migrate sessions-month-layout` separately moves old flat/day files and diagram sidecars into month folders with dry-run/backups; it is explicit and never runs during init/update/hooks/MCP/Trace startup.
- Branch-session fuse (current unreleased worktree): `memory-seed session fuse --branch <branch>` dry-runs branch-local session entries and diagram sidecars before promotion, and `--apply` writes only during an in-progress `git merge --no-ff --no-commit <branch>`. Imported entries must be branch-only, chronological, immutable relative to base, and carry `branch: <branch>`. Diagram sidecars require a parent entry already on the base/main tree or accepted for promotion in the same fuse. Branch-side validation is scoped to files the branch changed (three-dot `git diff <base>...<branch>`) so unchanged base-tree legacy entries without `entry_id` do not block; base-side enumeration stays full for already-present and sidecar-parent lookups. All git-subprocess helpers decode strict UTF-8 (with `UnicodeDecodeError` caught) rather than the Windows cp1252 locale default.
- Indexed topics (completed 2026-07-15): `topics:` is a first-class 1-3-slug entry field resolved against the deploy-once project-local `.memory-seed/topics.yaml` (this repo: 19 canonical topics + aliases; seed: minimal generic starter). Parser/retrieval exposure, alias-expanded filtering, `topics list`/`check`, live+seed authoring guidance, Trace chronological topic chains, read-only MCP topic tools, and deterministic `topics suggest --from <file>` are shipped. Plan: `docs/5_Completed/memory-trace-topic-neighbourhoods-plan.md`.
- Evolution edges and artifact lineage (core shipped in 2.18.0; Trace continuity completed 2026-07-15): typed `evolves:` plus read-time `evolved_by`, inverse-field and continuity validation, structured rename/migration/removal records, alias-aware `F:` overlap evidence, retrieval freshness fields, Decision Harvest prompts, and derived Trail continuity lanes are shipped. The Trail derives display lanes without adding authored graph edges. Spec: `docs/3_Spec/graph-edge-contract.md`; plan: `docs/5_Completed/evolution-edges-plan.md`.
- One-step branch integration (current unreleased worktree): `memory-seed session merge-branch --branch <branch> [--dry-run]` wraps fuse dry-run, `git merge --no-ff --no-commit`, session-path reset to base content, fuse apply, staging, and the merge commit into one command, added after two incidents where the manual fuse steps were skipped and raw git line-merges landed session entries out of chronological order. Fails closed: fuse issues abort before any merge state exists; non-session conflicts leave the merge in progress for the named conflict owner (never `merge --abort`); requires a clean working tree and names the dirty paths when refusing. `agent_collaboration.md` (live + seed) now points integration at `session merge-branch` first, with `session fuse` kept as the lower-level primitive for manually inspected merges. Fuse stays an explicit command, not a git merge driver, per the recorded design decision.
- Configurable integration mode (completed 2026-07-15): `integration_mode: local-merge|pr` is a project-local default read fail-open as `local-merge`, surfaced by ESR, obeyed by live+seed agent contracts, and implemented by mode-aware `session integrate` plus `session open-pr`. Bootstrap may suggest a mode but requires human confirmation. Plan: `docs/5_Completed/configurable-integration-mode-plan.md`.
- Related-entries generation P1 (shipped 2.13.0): `build_related_entry_graph()` in `semantic_cache.py` builds the bidirectional related-entry graph (stored outbound edges + inbound backlinks computed only from resolvable refs; accepts a pre-extracted `chunks=` corpus to avoid re-parsing). Exposed read-only via `memory-seed link suggest` (ranks **older** candidate entries to link, reuses `rank_memory_chunks`, prints a paste-ready snippet) and `memory-seed link show <entry_id>` (outbound + inbound backlinks). Forward-only authoring + read-time bidirectional traversal preserves append-only; backfill between pre-existing entries and an optional `link add` writer are deferred (P2). Scope/decisions in `docs/2_Todo/completed/related-entries-generation-plan.md`.
- Session-log-check escalation (current unreleased worktree): `session-log-check.py` (live + seed) now writes a gitignored `.memory-seed/.session-log-check-state` (JSON, fail-open on corruption/unreadable) tracking the last-seen entry timestamp and a `consecutive_misses` counter. The underlying 15-minute staleness check is anchored to the last logged entry's own timestamp and was already immune to turn frequency; what it could not detect was whether a fired reminder went unaddressed. A stale check that repeats with no new entry appearing in between now escalates from the base reminder to explicit "repeated" wording naming the count and citing the discipline-failure framing already in `agent-rules.md`; a new entry appearing resets the counter. Reminder language was also tightened: leads with the imperative, enumerates concrete triggers (file changes, `git push`/`merge`/`rebase`/delete, any decision), and states D/R as required on every entry rather than framing DRAFT labels as decision-only.
- Authoring-loop MCP tools (current unreleased worktree): `mcp_server.py` adds read-only tools so the LLM authoring loop matches the retrieval loop — `memory_link_suggest` and `memory_link_show` wrap `suggest_related_entries`/`build_related_entry_graph` (paste-ready `related_entries` candidates and graph-node traversal), `memory_session_target` resolves the append target (`create=False`, never writes), and `memory_entry_id` computes the canonical deterministic entry id from metadata (added 2026-07-12 after the corpus was found full of hand-rolled ids). All three are documented under `history_retrieval.md`'s authoring-support section, keeping branch/fuse coordination in `agent_collaboration.md`. The CLI `session` group help was relabeled to cover the write-capable `fuse` subcommand, and the two `migrate` subcommands now cross-reference each other.
- Risk signaling skill (shipped 2.16.0): `.memory-seed/skills/risk_signaling.md` adds qualitative Proceed / Proceed-and-flag / Propose-and-wait / Stop tiers and STOP categories for destructive, irreversible, security/trust-boundary, shared/control-plane, external-communication, and financial actions. Registered in the live and seeded trigger registries; cross-referenced from collaboration and security triage.
- Encoding hardening (current unreleased worktree): `memory-seed encoding check` reports UTF-8/BOM/newline/NFC drift, likely mojibake, and implicit production Python text I/O; `encoding repair` previews or atomically repairs mechanically safe BOM/newline/NFC drift after timestamped backup. Invalid UTF-8 and likely mojibake remain manual. Encoding policy stays owned by Memory Seed rather than being duplicated in Memory Trace, and `doctor` provides a non-fatal summary.
- Memory Trace UI (current shipped-but-unreleased surface): the human review UI has a separate source boundary under `memory-trace/`, but its public install target is `memory-seed[trace]` with the `memory-trace` command. The old `memory-seed lense` route is a deprecated compatibility shim. Markdown session files remain the source of truth; Trace exposes searchable memory, filters, graph, Trail (commit-accurate merges, typed lifecycle routes, topic chains, and derived continuity lanes), reader/details, worktree switching, and sidecar diagrams. Deterministic timeline Evidence Packs are available from `memory_trace.evidence` with no provider or write path; provider/local-model summaries remain Phase 2 and non-authoritative. Assets are content-hash versioned at serve time and `--static-root` serves another checkout's UI.
- Session-authoring and end-of-turn tooling (current shipped-but-unreleased surface): lifecycle-edge link sidecars, `session append`/`reorder`/`entry-id`, `memory-seed esr`, trailer stamping, and `memory-seed link audit --date <date> --apply` are implemented. The apply path creates only inert, idempotent `classify_pending` stubs with commented candidate evidence; humans must classify and approve live edges, `links check` warns on unresolved stubs, and ESR counts them. Spec: `docs/3_Spec/lifecycle-edge-linking-sidecars.md`.
- ESR generalization (2.11.0): the "End Of Turn" routine in `agent-rules.md` (+ seed twin) now runs a consolidation review (promote durable facts → `index.md`/`policy.md` via `memory_consolidation`) and a baseline-promotion check (flag generic adaptations, record in `.memory-seed/plans/`, create-if-needed). Shipped as a seeded `/esr` command via two `SeedFile`s: `.claude/commands/esr.md` (agent=claude, version-tracked frontmatter, refreshes on update) and `.gemini/commands/esr.toml` (agent=gemini, deploy-once via `_is_runtime_local_file` since TOML carries no version marker). Codex/Cursor run the routine from `agent-rules.md`. No blocking `Stop` hook (deliberate — evolution needs reasoning + approval).
- User-aware session targets (2.10.0, month-grouped after current work): user identity is opt-in and local-first. Resolution order is explicit CLI/function argument, `MEMORY_SEED_USER`, gitignored `.memory-seed/local.yaml`, then shared flat behavior. `session_target()` returns `sessions/YYYY-MM/YYYY-MM-DD.md` when no user is configured or fewer than 2 participants are registered, and `sessions/YYYY-MM/YYYY-MM-DD/<user>.md` when a valid slug is active and the per-user gate is met; `--create` initializes per-user file frontmatter with `schema_version: 2`, `session_date`, immutable `msm_` file `hash_id`, `user`, and `created_at`. Hooks are user-aware and grouped-path-aware: `session-log-check.py` checks only the active user's target, while `session-start-context.py` injects the active user's latest entry and lists same-day co-contributor files by count.
- Agent-selective install (2.6.0 plus current unreleased UX refinement): `init` installs only the chosen agents' files; the set is persisted in `.memory-seed/project.yaml` (`agents:` list) and respected by `doctor`/`update`. Interactive init now presents agent integrations as an opt-out step with all agents selected by default; `--agents none` writes the explicit zero-agent state and `--no-agent-prompt` skips the prompt. Driven by the `KNOWN_AGENTS`/`_AGENT_MERGES`/`_AGENT_UNINSTALLS` registries in `core.py` and a per-`SeedFile` `agent` tag. Absent `project.yaml` means all agents for legacy projects; present-but-empty `agents:` means zero agents. `agents list` reports selected and ignored agents. `agents add/remove` reconfigure; `remove` strips only our entries (foreign config preserved), never deletes shared dirs, backs up first. `codex`/`cursor` have no routing file (read `AGENTS.md` natively).

## Session Memory

- Append meaningful work notes to the active session target (`memory-seed session target`), which is month-grouped flat (`.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md`) unless the per-user participant gate selects a grouped per-user file.
- Keep session entries concise, publishable, and free of secrets.
- Older `.AGENTS/sessions/` logs were migrated into `.memory-seed/sessions/` for the v2 meta-test.
