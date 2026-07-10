# Changelog

All notable changes to Memory Seed are summarized here.

## Unreleased

- Implemented indexed topics P1 (topic-neighbourhoods plan, Phases 0-3): meaningful session
  entries carry 1-3 `topics:` slugs resolved against the new deploy-once project-local
  `.memory-seed/topics.yaml` vocabulary (canonical slugs + aliases, slug rule
  `^[a-z0-9][a-z0-9_-]{0,63}$`, `update` never overwrites project curation; seeded projects get a
  minimal generic starter). `MemoryChunk.topics` parses the stored field; retrieval dicts expose
  it; `memory_search` gains an opt-in alias-expanded `topics` pre-ranking filter (fail-open, no
  effect when unused). New `memory-seed topics list` and `memory-seed topics check` commands
  validate the vocabulary and entry usage (unknown/malformed/duplicate/collision errors;
  deprecated-use and >3-count warnings; unused-topic info) - deliberately separate from
  `links check`, since topics are membership, not a graph edge kind. `session_logging.md`
  (live + seed) documents the field and the read-the-index-first authoring rule. This repo's own
  vocabulary was derived from the 62 slugs already in use (user-approved 19-canonical
  consolidation with every observed slug preserved as canonical or alias). Trace rendering of
  indexed topics and MCP topic-management tools stay deferred (plan Phase 4).

## 2.17.0 - 2026-07-10

- Recorded two shipped-but-unchangelogged features found by the 2026-07-10 goal-run review:
  (1) **Memory Trace Phase-2 extraction** - the review UI moved into the standalone `memory-trace/`
  distribution (own `pyproject.toml`, `memory_trace` package, `memory-trace` command, static
  assets; core sheds `fastapi`/`uvicorn`; `memory-seed[lense]` and `memory-seed lense` are
  deprecation shims), with Arc 2 UI work (reader subsection highlighting, Trail view with branch
  lineage + supersedes edges, client-side Mermaid rendering with source fallback). Publication of
  `memory-trace 0.1.0` waits on core 2.17 plus PyPI project setup.
  (2) **Skill profiles and CLI skill management** - fresh projects install core skills by default,
  optional profiles can be selected during `init`, ignored optional skills stay ignored on
  `update`, and `memory-seed skills list|ignored|add|remove` rewires skill files and registry
  entries.
- Fixed the fuse/merge-branch chronological rewriter butting each session-entry heading against
  the previous entry's last line: `_write_chronological_session_file` and
  `_write_chronological_diagram_file` now join entries with a blank line, restoring the
  hand-appended log's separation. Files previously rewritten cramped are normalized the next time
  a fuse touches them; a regression test pins the one-blank-line contract.
- Added typed evolution edges and artifact lineage (evolution-edges plan): entries can declare
  `evolves:` - "extends that decision, which remains valid" - with a computed, read-time-only
  `evolved_by` inverse that never dampens `importance_score` and never feeds `exclude_superseded`
  (the semantic line vs. `supersedes`); `links check` gains per-kind forward-only guards
  (`dangling/self/postdates/cycle` for evolves), the `authored-inverse-field` guard (a stored
  `superseded_by:`/`evolved_by:` key is now a named integrity error - append-only enforcement),
  and `malformed-continuity`. The new structured `continuity:` field records artifact renames,
  migrations, and removals (`kind`/`from`/`to`; `to` forbidden on removal) as historical labels;
  recorded renames feed a transitive alias table in `link suggest`/`memory_link_suggest`, which
  now also applies a rarity-weighted `F:` file-overlap boost with per-suggestion shared-file
  evidence (boost-only: hub files count ~nothing, absent `F:` is never penalized). Every
  `memory_search` result now carries computed `superseded_by`/`evolved_by` so consumers see
  retired/evolved status at retrieval time without extra calls - additive fields, ranking and
  order untouched. Decision Harvest (live + seed skills) gains the lifecycle prompts: does a
  harvested decision replace/remove/evolve an earlier entry, and did the turn rename, relocate,
  or remove any artifact.
- Added `memory-seed session merge-branch --branch <branch> [--dry-run]`: one-step task-branch
  integration that wraps the previously manual dance (fuse dry-run, `git merge --no-ff
  --no-commit`, `session fuse --apply`, commit) so session entries always land in timestamp order
  without a separate fuse step to forget - added after two real incidents where skipping that step
  let raw git line-merges land entries out of chronological order. Fails closed: fuse issues abort
  before any merge state exists; non-session conflicts leave the merge in progress for manual
  resolution (never `merge --abort`); branch-touched session paths are reset to base content before
  the fuse apply, which defeats both conflict markers and silent out-of-order auto-merges; requires
  a clean working tree and names the dirty paths when refusing. `agent_collaboration.md` (live +
  seed) now routes integration through `session merge-branch` first, keeping `session fuse` as the
  lower-level primitive for manually inspected merges. No new MCP tool: MCP stays read-only for
  this workflow.
- Hardened the `session-log-check.py` Stop hook against reminders going unaddressed: a gitignored
  `.memory-seed/.session-log-check-state` (fail-open on corruption) tracks consecutive stale checks
  with no new session entry appearing in between, escalating from the base reminder to explicit
  "repeated" wording (naming the count, citing `agent-rules.md`'s discipline-failure framing) instead
  of repeating identically forever; a new entry resets the counter. The 15-minute staleness check
  itself is unchanged and was already anchored to the last logged entry's own timestamp rather than
  to hook-invocation frequency. Reminder language was also tightened: leads with the imperative,
  names concrete triggers (file changes, `git push`/`merge`/`rebase`/delete, any decision), and
  states D/R as required on every entry instead of framing DRAFT labels as decision-only.
- Fixed two `session fuse` bugs that made it unusable on this repo's own branches. (1) The git
  subprocess helpers (`_git_text`, `_git_show_text`, `find_trailer_commits`) now decode output as
  strict UTF-8 and catch `UnicodeDecodeError`, instead of defaulting to the Windows locale (cp1252)
  and crashing / silently truncating on non-ASCII session content. (2) Branch-side validation is now
  scoped to the files the branch actually changed (three-dot `git diff <base>...<branch>`), so
  unchanged base-tree files — including legacy pre-schema logs that carry no `entry_id` — no longer
  block the fuse; base-side enumeration stays full for already-present and sidecar-parent lookups.
- Added three read-only authoring-support MCP tools so the LLM's write-side loop matches its
  retrieval loop: `memory_link_suggest` (rank older entries to link, returning paste-ready
  `related_entries`), `memory_link_show` (one entry's related-entry graph node — outbound/inbound
  edges, supersession, importance, linked-commit count), and `memory_session_target` (resolve the
  session-log append target without ever creating the file). They wrap the existing
  `suggest_related_entries`/`build_related_entry_graph`/`session_target` functions, are routed through
  `history_retrieval.md`, and keep all session writing on the CLI/direct-file path. The CLI `session`
  group help was relabeled to cover its write-capable `fuse` subcommand, and the two `migrate`
  subcommands now cross-reference each other.
- Added a warning-only `memory-seed branch status [--json]` command that reports current Git
  branch/worktree posture and recommends a task branch plus `git merge --no-ff` when distinct
  feature or proposal work is happening directly on the integration branch. No hard block — small
  fixes, release prep, and emergency repairs may still proceed on the integration branch.
- Tightened session-log closeout: `session_logging.md`/`end_of_turn.md` now route through an
  explicit **Decision Harvest** step before choosing the entry shape (single DRAFT vs. multi-decision
  D1/D2), so durable choices made in a turn are captured individually rather than compressed into one
  broad record. Decision-diagram sidecar guidance changed from an optional consideration to a
  **positive trigger** for branch/merge topology, old-to-new layout migrations, schema/compatibility
  flows, multi-agent concurrency, command lifecycle flows, and retrieval/data pipeline decisions.
- Added the Phase 1 UTF-8 text contract: `.editorconfig`, `.gitattributes`, `memory_seed.text_files`
  helpers for UTF-8/LF/NFC text and Unicode-preserving JSON, README documentation, MCP
  Unicode-preserving JSON output, and regression tests for non-ASCII round trips.
- Completed encoding hardening: `memory-seed encoding check` reports invalid UTF-8, UTF-8 BOMs,
  CRLF line endings, non-NFC text, likely mojibake, and implicit text-mode Python I/O. The new
  `memory-seed encoding repair [--dry-run]` command atomically repairs safe BOM/newline/NFC drift
  after writing timestamped backups, while invalid UTF-8 and likely mojibake remain blocked for
  manual review. `doctor` now summarizes encoding findings non-fatally.
- Added safe process-management and upgrade commands for both packages: `memory-seed processes`,
  `memory-seed shutdown`, and `memory-seed upgrade`, plus matching delegated commands for
  `memory-trace`. Shutdown is confirmation-gated by default, supports `--dry-run`, `--yes`, and JSON
  output, excludes the current control command, and only targets processes whose executable path or
  command line clearly belongs to the package. `upgrade` blocks on failed shutdown and can run
  `uv`, `pipx`, or `pip` upgrades via `--manager`.
- Made agent integration selection a first-class `init` step: interactive init now presents an
  opt-out agent prompt with all supported agents selected by default, `--agents none` installs only
  the shared runtime, `--no-agent-prompt` skips the prompt, and init/`agents list` report both
  installed and ignored agents.
- Aligned `proposal_lifecycle.md` with the repository's numbered docs taxonomy
  (`docs/1_Inbox`, `docs/2_Todo`, `docs/3_Spec`, `docs/4_Reference`) while preserving the generic
  bootstrap taxonomy (`docs/inbox`, `docs/todo`, `docs/reference`) for newly initialized projects.
- Slimmed `agent-rules.md` further into a startup contract and added optional
  `skill_architecture.md` under the new `governance` skill profile. The new skill owns guidance for
  skill/profile boundaries, concise trigger-registry entries, and seed/live parity; `agent-rules.md`
  now points to it before agents move procedural guidance between rules, policy, and skills.
- Switched new session writes to month-grouped targets:
  `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md`,
  `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD/<user>.md`, and grouped diagram sidecars under
  `.memory-seed/sessions/diagrams/YYYY-MM/YYYY-MM-DD.md`. Core discovery, retrieval, MCP/Trace
  parsing, `compact`, hooks, and `links check` continue reading legacy flat/day layouts. Added the
  explicit `memory-seed migrate sessions-month-layout [--dry-run]` command to reorganize old files
  with backups; no migration runs automatically during init/update/hooks/MCP/Trace startup.
- Added branch-session fuse hardening for multi-agent integration: `memory-seed session fuse --branch
  <branch>` previews branch-local session entries and diagram sidecars, while `--apply` is gated to
  an in-progress `git merge --no-ff --no-commit`. Existing entries/sidecars are immutable, imported
  entries must carry matching `branch:` metadata, sidecars require a parent entry already on base or
  accepted in the same fuse, and MCP now exposes read-only `memory_branch_status` and
  `memory_session_fuse_preview` tools routed through `agent_collaboration.md`.

## 2.16.0 - 2026-07-05

- **Public retrieval service (`memory_seed/retrieval.py`), Memory Trace distribution plan Phase 1:**
  the MCP-coupled search orchestration and result-dict contract moved verbatim out of
  `mcp_server.py` into an MCP-independent public service (`search_memory`, `get_chunk`,
  `resolve_semantic_provider`, `format_search_results`, `ranked_to_dict`, `chunk_to_dict`). The MCP
  server is now a thin JSON-RPC wrapper with a byte-identical tool contract (parity tests assert
  `call_tool` == service output); Memory Trace consumes the same service. This is the frozen
  surface the companion UI package imports.
- **Entry-level result rollup:** `EntryRollup` / `rollup_entry_matches()` / `rollup_entry_results()`
  in the retrieval service collapse ranked entry+section matches into one visible entry-level result
  (entry chunk preferred as representative, matching sections preserved as highlight metadata,
  `score_source` = `entry`|`section-rollup`, `best_match_chunk_id`). Memory Trace entry-granularity search
  consumes the shared grouping; a strong subsection match can now drive an entry's score without
  appearing as a separate selectable record. `granularity=section|all` and the MCP contract are
  unchanged. Memory Trace UI copy says "entry"/"session entry" and renders "Matched section" chips.
- **Session decision diagram sidecars, Phase 1:** optional authored reasoning diagrams appended to
  `.memory-seed/sessions/diagrams/YYYY-MM-DD.md` — one dated file per day, mirroring the session-log
  filename convention for filesystem readability; each diagram is a `## <timestamp> - <title>` heading
  block naming `entry_id` in a fenced yaml block, followed by fenced ```` ```mermaid ```` block(s).
  `links check` validates them (`malformed-diagram`, `orphan-diagram`, `diagram-date-mismatch`;
  deterministic checks only, sidecars always optional).
  `retrieval.entry_diagram_sidecars()` surfaces per-entry sidecar metadata; `get_chunk` grows an
  opt-in `include_diagrams` flag the MCP tool never passes; Memory Trace's chunk view carries a `diagrams`
  metadata list. Authoring guidance shipped in `session_logging.md` + `end_of_turn.md` (live + seed).
- Recorded the intermediate Memory Trail name availability check in `memory-trail-renaming-plan.md`:
  `memory-seed-trail` is unregistered on PyPI, but `memory-trail` is a live same-niche product —
  the later product-naming decision settles on Memory Trace as the package/product and Trail as an
  internal evolution view.
- Added `docs/3_Spec/graph-edge-contract.md`: the single reference for how decision-graph edges
  (`related_entries`, `supersedes`, `commits`) and derived metrics (`inbound_relation_count`,
  `importance_score`, `connectivity`, `commit_reference_count`) are defined, computed, and read across
  CLI, MCP, Memory Trace, and `links check`. Codifies the standing rules: read the canonical graph,
  keep git out of the hot path, expose before you rank, one name one meaning.
- Exposed `commit_reference_count` on `memory-seed link show` and `memory_get_chunk`: the count of
  distinct commits linking to an entry (its `commits:` field ∪ `Memory-Entry:` trailer, deduped by
  SHA). Computed caller-side via `commit_reference_ids()` so the graph reader stays git-free.
  Deliberately a standalone read-only field, **not** folded into `importance_score` (that would make
  the score git-context-dependent and inconsistent across surfaces); composing it into a score is a
  later evidence-gated ranking experiment.
- Memory Trace graph nodes now carry `importance_score`, and a "Size:" toggle sizes nodes by either
  link `connectivity` (default) or `importance_score`. The preference persists in local storage; the
  toggle is client-side (no reload).
- Added `proposal_lifecycle.md` to the seeded skill set and trigger registry. It formalizes proposal
  movement through inbox -> todo -> completed/reference lanes, including status blocks,
  completed-proposal movement rules, and roadmap/audit update surfaces.
- Added `risk_signaling.md` to the seeded skill set and trigger registry. It defines qualitative
  Proceed / Proceed-and-flag / Propose-and-wait / Stop action tiers plus STOP categories for
  destructive, irreversible, security/trust-boundary, shared/control-plane, external-communication,
  and financial actions. Cross-referenced from `agent_collaboration.md` and `security_triage.md`;
  guidance-only, with no new session schema or automated gate.
- Added a Dependency Strategy to `agent_collaboration.md` (+ seed twin): three dependency tiers
  (`none`/`isolated`/`dependency-changing`), four new task-packet fields (`dependency_tier`,
  `dependency_setup`, `dependency_definition_policy`, `dependency_shared_cache_policy`), dependency
  definition files/lockfiles named as orchestrator-owned shared files, shared-cache-vs-shared-environment
  guidance, and an optional tmux-as-control-room note. Documentation-only; no CLI scaffold. Plan moved
  to `docs/2_Todo/completed/worktree-dependency-strategy-plan.md`.
- Added `docx_render_windows.md` to the seeded skill set and trigger registry: Windows-safe DOCX
  render fallback covering the LibreOffice `UserInstallation` profile-URI hang, a bounded two-step
  DOCX→PDF→PNG render pattern, stale-process cleanup, Word field/TOC refresh before render QA,
  page-level visual inspection rules, and a single-writer render / read-only validator collaboration
  boundary. Cross-referenced from `office_document_editing.md`.
- Kept `MEMORY_SEED_LENSE_CACHE_ROOT` working as a compatibility alias for Lense cache placement;
  `MEMORY_SEED_CACHE_DIR` remains the preferred generic cache variable.

## 2.15.0 - 2026-07-04

- Added an opt-in `exclude_superseded` filter to `memory_search` (default `false`). When set, entries
  with a non-empty computed `superseded_by` are dropped from that query's results only — an opt-in
  narrowing like `date_from`/`date_to`, never a default and never a hard exclusion otherwise, so
  superseded entries stay fully retrievable by default (deprioritized via `importance_score`, not
  hidden). Backend-only; no CLI or UI default. From `docs/2_Todo/completed/exclude-superseded-filter-plan.md`.
- Exposed `importance_score` (ranking P1b): `inbound_relation_count` dampened by a fixed multiplier
  (`SUPERSEDED_IMPORTANCE_DAMPING = 0.25`) when the entry has any inbound `supersedes` edge —
  computed on `RelatedEntryNode`, shown by `memory-seed link show` (flagged when dampened) and
  returned in `memory_get_chunk` metadata. This completes the supersession harmony contract: a
  well-cited but retired decision ranks below a live, moderately-cited one, while staying fully
  retrievable (never hidden). Supersession edges never inflate the underlying count — the dampener
  is a post-hoc override. Read-only; default `memory_search` ranking is untouched. From
  `docs/2_Todo/completed/interaction-frequency-ranking-plan.md` (P1b) and `docs/2_Todo/completed/supersession-edges-plan.md`
  (harmony contract).
- Exposed `inbound_relation_count` (ranking P1a): the count of inbound `related_entries` backlinks an
  entry has accumulated (how many other entries reference it), shown by `memory-seed link show` and
  returned in `memory_get_chunk` metadata. Read-only — default `memory_search` ranking is untouched,
  per the exposure-before-ranking-changes policy. This is the directional importance-signal precursor.
- Renamed the Trace graph-node `related_degree` field to `connectivity`. Its computation is
  unchanged (combined inbound+outbound `related_entries` edges, used for node sizing) — the rename
  resolves a collision with the new inbound-only `inbound_relation_count` above, since the two count
  genuinely different things. The two-field split is documented in
  `docs/2_Todo/completed/interaction-frequency-ranking-plan.md`.
- Added git commit <-> decision entry linking (P1): a `Memory-Entry: <entry_id>` commit-message
  trailer convention (documented as a Working Principles bullet in `agent-rules.md` + seed twin)
  plus an optional `commits:` entry-YAML field of full 40-character SHAs, backfillable only while
  the entry is still the newest one (same-turn scoping, no historical edits). New read-only
  `memory-seed link commits <entry_id>` prints both sources: the stored field and a
  `git log --all --grep` trailer scan. `links check` rejects short/malformed hashes always
  (`malformed-commit-hash`) and unknown hashes when a `.git` repository is present
  (`unknown-commit`); outside a git repo, existence checks skip cleanly. From
  `docs/2_Todo/completed/git-commit-entry-linking-plan.md`.
- Added typed supersession edges (P1): an optional `supersedes:` list in entry YAML marks earlier
  decisions an entry replaces, kept strictly separate from `related_entries`. The read-time inverse
  (`superseded_by`) is computed in `build_related_entry_graph()` the same way inbound backlinks are,
  and exposed via `memory-seed link show` and `memory_get_chunk` (search results carry the stored
  `supersedes` field). `links check` validates the new edge: dangling refs (`dangling-supersedes`),
  self-references (`self-supersedes`), forward-only violations where the target postdates the
  referencing entry (`supersedes-postdates`), and same-minute cycles via a DFS (`supersedes-cycle`).
  Superseded entries stay fully retrievable — supersession deprioritizes, never hides. Schema
  documented in `skills/session_logging.md` (+ seed twin). From `docs/2_Todo/completed/supersession-edges-plan.md`.

## 2.14.0 - 2026-07-03

- Session-log layout now gates on the `participants:` registry, not just a configured user. `session_target()` only switches to per-user files (`sessions/YYYY-MM-DD/<user>.md`) once `.memory-seed/project.yaml` lists 2 or more participants; with 0 or 1, it stays on the shared flat file even with a local user configured, since per-user files exist to avoid concurrent-author conflicts that don't arise until there's a second author. An explicit `--user <slug>` CLI override still bypasses the gate. The SessionStart hook's own user resolution mirrors this so it keeps reading the same file `session_target()` writes to.
- Added a one-time identity-setup offer to the SessionStart hook: if no local identity is configured (no `MEMORY_SEED_USER`, no `.memory-seed/local.yaml`), it suggests `memory-seed user set <slug>` plus a `participants:` entry, then never repeats (tracked by a gitignored `.memory-seed/.identity-offer-stamp`). Skippable; most projects are solo and don't need it.
- `memory-seed doctor` now warns (non-fatal) when a configured local user's slug has no matching `participants:` entry in `.memory-seed/project.yaml`, so `user_initials` stays resolvable for multi-user tooling.
- Documented the identity/layout model in `agent-rules.md` and `skills/session_logging.md`.
- Fixed `memory-seed links check` silently skipping entry-level `related_entries` validation for legacy-flat session files. The dangling-ref scan was scoped inside a `per-user-day`-only branch; a dangling `related_entries` ref in a `sessions/YYYY-MM-DD.md` file passed with no warning. The entry-level scan (each entry's fenced `` ```yaml `` block, same shape in both layouts) now runs unconditionally, while the genuinely per-user-file-specific checks (frontmatter, `hash_id`, user-slug) remain scoped to per-user files.
- Added two Working Principles to `agent-rules.md`: a decision-ladder-before-adding-code check with a habit of noting deferrals, and a reminder not to strip terse validation/ownership guards without understanding what they protect against. Also added regression tests for two previously-uncovered guards (`_valid_session_date` and the MCP ownership-preservation check in the `.mcp.json`/`.cursor`/`.gemini` merge functions) so a future simplification pass has a test that fails if either is removed.
- Added a third Working Principles bullet to `agent-rules.md`: default to plain text, reserve Mermaid for genuinely spatial/temporal/concurrent structure, keep blocks small, and check both syntax and semantic freshness (a stale roadmap diagram is as misleading as a broken one). From `docs/2_Todo/completed/mermaid-usage-guidance-plan.md`.
- Added a failed-approaches rule to `skills/session_logging.md`'s Reason Rules: an approach that was attempted and failed (or proved incompatible) during a session must be logged under `A` even when not asked — one line stating what was tried and why it failed, as empirical evidence for future sessions. From `docs/2_Todo/completed/failed-approaches-logging-plan.md`.
- Added the named "Fan-Out Recipe: Explore / Plan / Implement / Validate" to `skills/agent_collaboration.md`: a 9-gate pipeline (Scope through Final Handoff) with a bounded review-to-rework loop capped at 2 iterations, preflight identity verification for both writers and read-only explorers, and orchestrator-only shared-file writes. The task packet gained `base_sha`, `expected_pwd`, `integration_artifact`, `capability_tier`, `shared_file_policy`, `conflict_owner`, `preflight`, and `review_loop` fields, plus vendor-neutral capability-tier guidance (planning and review both warrant the top tier). From `docs/2_Todo/completed/agent-fanout-workflow-plan.md`.

## 2.13.0 - 2026-07-01

- Added `memory-seed lense`, an optional local FastAPI/Uvicorn browser UI for
  searching, filtering, reading, graphing, and timeline-scanning Memory Seed
  session history. Install with `pip install "memory-seed[lense]"`; without the
  extra the command prints the install hint.
- Included the Memory Lense static UI assets in the package distribution.
- Added the universal `agent_collaboration.md` skill for Git-first subagent, branch,
  worktree, merge-conflict, and multi-developer agent workflows.
- Extracted detailed control-plane procedures from `agent-rules.md` into seeded lazy
  skills: `history_retrieval.md`, `session_logging.md`, `end_of_turn.md`,
  `memory_hygiene.md`, and `subproject_runtime.md`. `agent-rules.md` now keeps
  startup-safe summaries and explicit skill pointers, and seeded ESR commands point
  to the `end_of_turn.md` checklist.
- Fixed the packaged seed inventory so every `SeedFile` source is included in
  wheel/sdist package data, including `/esr` command files, lifecycle hooks,
  document skills, and the new lazy skills.
- Added `memory-seed link suggest [--for <entry_id>] [--top-k N]` - a read-only command that ranks
  **older** session entries to link from a target entry (default: the newest entry), excludes the
  target and its already-linked entries, and prints a copy-pasteable `related_entries:` snippet. It
  reuses the existing ranker with recency disabled so similarity drives the order.
- Added `memory-seed link show <entry_id>` - prints an entry's stored outbound `related_entries`
  edges plus its computed inbound backlinks, so the related-entry graph is **bidirectional at read
  time** without ever editing a historical entry.
- Added `build_related_entry_graph()` in `semantic_cache.py`, the canonical bidirectional
  related-entry graph (outbound as stored; inbound computed only from resolvable refs) for MCP and
  future UI consumers. Scope + decisions in `docs/2_Todo/completed/related-entries-generation-plan.md`.

## 2.12.0 - 2026-06-15

First batch of multi-user Phase 3 increments from the reviewed 3.0 plan.

- **Added session-memory integrity validation** (`memory-seed links check`) — the first increment of the 3.0 multi-user roadmap (Phase 3). It scans both legacy-flat (`sessions/YYYY-MM-DD.md`) and per-user (`sessions/YYYY-MM-DD/<user>.md`) layouts and reports: duplicate `entry_id`s (the 32-bit-ID collision risk), duplicate file `hash_id`s, dangling `related_entries`/`related_memories` references, and per-user-file frontmatter problems (filename↔frontmatter `user` or `session_date` mismatch, missing/malformed `hash_id`, unsupported `schema_version`, invalid user slug). Each issue names the source file and the offending value; the command **exits non-zero** on any issue so it works as a CI gate. It validates entry-level `related_entries` inside session-entry YAML as well as file-frontmatter related refs, resolving both legacy `ms-` IDs and new `mse_` IDs.
- `memory-seed doctor` now surfaces a one-line, non-fatal summary when integrity issues exist, pointing at `links check` for the full report (it does not change doctor's pass/fail).
- New generated session `entry_id` values now use deterministic 80-bit `mse_` IDs encoded as 16 lower-case Base32 characters. Existing `ms-` entry IDs remain valid and are never rewritten.
- `memory_search` / `memory_get_chunk` now expose `session_date`, `path`, per-user `user`, `file_hash_id`, and entry-level `related_entries`; `memory_search` accepts `user`, `date_from`, and `date_to` filters applied before ranking.
- `.memory-seed/project.yaml` now supports a `participants:` registry alongside the existing `agents:` selection. `read_project_participants()` parses valid participant entries fail-open, and agent-selection reads/writes preserve the participant block.
- Added `memory-seed migrate sessions-layout`, a conservative migration command that splits legacy flat `sessions/YYYY-MM-DD.md` files into `sessions/YYYY-MM-DD/<user>.md` files using `.memory-seed/project.yaml` participant initials, supports `--dry-run`, preserves entry IDs, backs up migrated sources, removes migrated flat files to avoid dual-read duplicate IDs, and blocks ambiguous or unsafe merges.
- Documented the optional entry-level `related_entries` field in the `agent-rules.md` session-log schema so agents can author the graph edges that `memory_search` and `links check` already read and validate.
- Bumped control-plane version from `2.11` to `2.12`.

## 2.11.0 - 2026-06-15

- **Generalized the end-of-session routine (ESR) and shipped it as a seeded command.** The "End Of Turn" routine in `agent-rules.md` now also runs a **consolidation review** (promote durable, reusable facts from the session logs into `index.md`/`policy.md` via the `memory_consolidation` skill) and a **baseline-promotion check** (flag any approved adaptation general enough to reuse beyond this project, recorded in `.memory-seed/plans/`, create-if-needed). Both are vendor-neutral and benefit every agent.
- The routine now ships as a seeded **`/esr`** command for agents with a verified repo-level command mechanism: Claude (`.claude/commands/esr.md`, version-tracked) and Gemini (`.gemini/commands/esr.toml`, deploy-once since TOML can't carry a version marker). Previously `/esr` existed only as a repo-local Claude convenience. Codex, Cursor, and any other agent run the same routine directly from `agent-rules.md` — that's where the canonical, vendor-neutral routine lives. The command is agent-selective (a Claude-only install gets only the Claude command, etc.).
- **No blocking end-of-turn hook.** A throttled `Stop` nudge hook was specced but deliberately not shipped: evolution needs reasoning and explicit user approval, which a hook cannot do; the command plus the routine cover it without nagging on every turn.
- Bumped control-plane version from `2.10` to `2.11`.

## 2.10.0 - 2026-06-14

- Added opt-in user-aware session targets. `memory-seed user set/show/clear` manages a gitignored `.memory-seed/local.yaml`; `MEMORY_SEED_USER` and `memory-seed session target --user <slug>` can override it.
- Added `memory-seed session target [--create]`. Without a configured user it keeps the legacy flat target (`.memory-seed/sessions/YYYY-MM-DD.md`); with a configured user it targets `.memory-seed/sessions/YYYY-MM-DD/<user>.md` and `--create` initializes per-user frontmatter with `schema_version: 2`, `session_date`, immutable `hash_id`, `user`, and `created_at`.
- Made session hooks user-aware while preserving legacy behavior. `session-log-check.py` checks only the active user's file, and `session-start-context.py` injects the active user's newest entry plus same-day co-contributor file counts.
- Bumped control-plane version from `2.9` to `2.10`.

## 2.9.0 - 2026-06-14

- Added read-only dual discovery for multi-user session logs. `memory_search`, `memory_get_chunk`, and `memory-seed compact` now read both legacy flat files (`.memory-seed/sessions/YYYY-MM-DD.md`) and per-day/per-user files (`.memory-seed/sessions/YYYY-MM-DD/<user>.md`, e.g. `2026-06-21/jean.md`).
- Preserved legacy write behavior and hooks. This release does not move existing logs, change where agents append new session entries, or resolve active users; SessionStart and session-log reminder hooks remain flat-layout until a later phase.
- Hardened fallback MCP chunk IDs for entries without `entry_id`: generated IDs now use the date-qualified source path, preventing collisions between same-named per-user files on different dates.
- Bumped control-plane version from `2.8` to `2.9`.

## 2.8.0 - 2026-06-14

- **Non-destructive routing into pre-existing entry-point files.** The four routing files Memory Seed manages — `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` — share their names with files other tools own (e.g. HyperFrames also uses `AGENTS.md`/`CLAUDE.md`). `init` and `update` now decide per file by ownership: a file that doesn't exist is written in full (unchanged); a file carrying our `memory-system-version` frontmatter is version-gated and archived+replaced (unchanged); a **foreign** file (no frontmatter) has a marker-delimited routing block — `<!-- BEGIN memory-seed -->…<!-- END memory-seed -->` pointing into `.memory-seed/` — **injected at the end, never overwriting the host's content** (even under `init --force`). On later updates the block is re-synced *in place* (the "second merge"), gated on content-equality so an unchanged stanza causes no churn. This mirrors the existing JSON-config merge philosophy (`_merge_grouped_hook`, the Copilot prompt-hook marker).
- **Behavior change:** a versionless entry-point file is now *merged* rather than *overwritten*. This retires the legacy "unversioned → archive under `unknown-*` + clobber" upgrade path. The fail-safe direction: when ownership can't be proven from frontmatter, append a block rather than destroy a file that is most likely host-owned or hand-edited.
- Added a `doctor` route-presence backstop (non-fatal `warnings` channel): if a `.memory-seed/` runtime exists but a present entry-point file is foreign and carries no routing block, it is flagged as an orphaned runtime ("`AGENTS.md` does not route into the `.memory-seed/` runtime — run `memory-seed update`"). Foreign routing files are no longer reported as version mismatches (the host owns the file; Memory Seed only manages its injected block).
- Bumped control-plane version from `2.7` to `2.8`. Existing projects running `memory-seed update` get the routing-merge behavior; a project whose `AGENTS.md`/`CLAUDE.md` is owned by another tool keeps that content and gains the routing block.

## 2.7.0 - 2026-06-14

- Promoted three **baseline seed additions**. Two new universal skill runbooks ship with `init`: `document_ingestion.md` (reading `.docx`/`.pdf`/`.pptx`/`.xlsx`/`.csv`/images as Markdown via markitdown, with per-format routing and fidelity caveats) and `office_document_editing.md` (field-safe surgical editing of Office documents that contain citations, captions, cross-references, or a TOC). Both get trigger-registry entries in `skills/index.md`. A new **Working Principles** section in `agent-rules.md` adds three cross-cutting rules: POC-gate a risky automated method before scaling it, state the verification split (what the agent can verify vs. what only the user can), and read share-aware copies of locked files.
- Added an **orphan & dead-artifact sweep** to the end-of-session routine. The "End Of Turn" section of `agent-rules.md` (and its seed twin, mirrored in this repo's `/esr` command) now includes a diff-scoped step: for everything the session added, confirm it is referenced somewhere (imported / registered / linked / routed) or remove it; for everything deleted or renamed, search for and resolve dangling references; flag scratch debris (temp files, commented-out code, half-removed features, stray untracked dirs, `*.bak`). The step is language-agnostic and never installs tools — if the project already declares a dead-code tool (vulture/ruff, knip, ArchUnit, cppcheck) the agent may run it, otherwise it just notes one is available. The sweep reliably catches orphan *files and features*; whole-codebase *dead code* remains a periodic tool job, stated explicitly so the routine does not over-promise.
- Added a deterministic **orphan-skill check** to `memory-seed doctor` (non-fatal `warnings` channel): any `.memory-seed/skills/*.md` runbook not registered in `skills/index.md` is flagged so it gets a trigger entry or is removed. This is the automatable backstop to the agent-performed sweep; it has deterministic ground truth and no false positives. (A session-log dangling-reference scan was deliberately *not* added — logs legitimately cite renamed, deleted, or example paths.)
- Bumped control-plane version from `2.6` to `2.7`. Existing projects running `memory-seed update` receive the updated `agent-rules.md` and `memory_doctor.md` skill.

## 2.6.0 - 2026-06-13

- Added **agent-selective install**. `memory-seed init` now accepts `--agents claude,codex` (and prompts interactively on a terminal) to install only the chosen agents' files — keeping repos clean (e.g. no `GEMINI.md` for a Claude+Codex user). `AGENTS.md`, the `.memory-seed/` runtime, and `.agents/` personas are always installed; only agent-specific routing files and per-agent hook/MCP configs are gated. The choice is persisted in `.memory-seed/project.yaml` (`agents:` list), which `doctor` and `update` respect (a deselected agent is never flagged missing or re-added). A project with no `project.yaml` behaves exactly as before (all agents). Added `memory-seed agents list|add|remove <agent>`; `remove` strips only Memory Seed's own entries (foreign config preserved) and backs up everything it touches. `codex` and `cursor` get no routing file — they read `AGENTS.md` natively.
- Added a **SessionStart orientation hook** (`session-start-context.py`). It reads the newest dated `.memory-seed/sessions/*.md` file directly and injects its path, all entry headings, and the most recent entry's body at session start, so agents establish current state by recency rather than semantic search (which ranks by topical similarity and can bury or omit the newest entry). Wired to Claude/Codex `SessionStart`, Gemini `SessionStart`, and Cursor `sessionStart` via `init`/`update`.
- Added **GitHub Copilot** as a supported agent. Copilot CLI: repo-local `.github/mcp.json` (`mcpServers` key, `type: stdio`) for `memory_search`/`memory_get_chunk`, plus a `sessionStart` **prompt** hook in `.github/hooks/memory-seed.json` (Copilot command hooks cannot inject context at sessionStart, and its `userPromptSubmitted`/`agentStop`/`sessionEnd` events do not support `additionalContext`, so it receives no per-turn reminders). VS Code Copilot: `.vscode/mcp.json` (`servers` key) + a thin `.github/copilot-instructions.md` router. The Copilot coding agent (github.com) reads `AGENTS.md` already; its MCP lives in repo/org settings (manual).
- **Fixed dead Gemini hook wiring.** Earlier versions wired Gemini's session-log and retrieval hooks to `Stop`/`UserPromptSubmit`, events Gemini does not expose, so they never fired. They now target `AfterAgent` (turn-end) and `BeforeAgent` (prompt-submit); `memory-seed update` strips the stale entries. The `--gemini` hook output now uses `hookSpecificOutput.additionalContext` as Gemini requires.
- Reconciled the per-prompt retrieval reminder (`memory-retrieval-check.py`) with the recency rule: it now points at `memory_search` for **topical** recall and defers "what's the latest" to the SessionStart/newest-file path, matching the new "Recency vs. Topical Retrieval" section in `agent-rules.md`.
- Bumped control-plane version from `2.5` to `2.6`. Existing projects running `memory-seed update` receive the new SessionStart hook, the Copilot wiring, the Gemini hook migration, and the reconciled reminder.

## 2.5.0 - 2026-06-04

- Added `.agents/` persona library. `memory-seed init` now ships six vendor-neutral agent persona templates (developer, content-creator, researcher, sales-rep, solo-founder, copywriter) under `.agents/`. Each persona file defines an identity, memory protocol pointing at `.memory-seed/`, operating rules, session discipline, skill routing, and an append-only `## Project Adaptations` section for traceable persona evolution. Persona files are runtime-local (deploy-once; `memory-seed update` never overwrites them) so project-specific customisations survive upgrades.
- Added `agent_name` field to session log entries. A new optional YAML field (`agent_name: <persona-slug>`) sits alongside the existing `agent_type` (LLM model/vendor) in every session entry. `memory_search` parses and returns it, enabling per-persona history queries. Old entries without the field are unaffected.
- Expanded `project-bootstrap.md` Step 9 — persona activation is now a five-sub-step guided flow: persona selection, personalization (entity name via pop-culture pick or user input; user name inferred from `git config`; business name inferred from project files with placeholders replaced in-file), skill routing (mapped skills table filled per persona role; gap detection with draft → approval → write for missing skills), `_registry.yaml` write with resolved metadata, and automatic onboarding of any unregistered `.agents/*.md` files dropped in after init.
- Expanded `agent-rules.md` Operating Mode Start with Step 9: if `.agents/_registry.yaml` exists, read it, load all active persona files, apply rules alongside `agent-rules.md` and `policy.md`, and record `agent_name` in all session entries. Expanded end-of-turn with Step 8: skill evolution — if a repeating workflow gap emerged, propose a draft skill file for user approval, then write it to `.memory-seed/skills/`, add a `persona:` trigger entry to `skills/index.md`, and update the persona's `### Role-Specific Skills` section.
- Added `copywriter-conversion.md` skill to the seed. Ships as a first-class universal skill with framework-selection decision table (AIDA, PAS, BAB, FAB, 4Ps, JTBD keyed to audience awareness level), developer-tool objection map, and format templates for README hero, landing page, Product Hunt tagline, email subject line, and GitHub description. Trigger entry in `skills/index.md` includes a `persona: copywriter` field; agents respect this and skip the skill when the copywriter persona is not active.
- Added `skills/index.md` trigger entries now support an optional `persona:` field scoping a skill to a specific active persona. Agents skip persona-scoped skills when the named persona is not active.
- Added bidirectional Didion ↔ Hopkins handoff protocol. A `## VII. Handoff Protocol` section in both the content-creator and copywriter persona templates defines a structured Copy Brief (Didion → Hopkins) and Repurposing Note (Hopkins → Didion) appended to the session log for the other persona to consume at startup. Neither persona reviews the other's work before publishing; Stark (solo-founder) holds the shipping decision.
- Added ESR slash command. `.claude/commands/esr.md` registers `/esr` in Claude Code, triggering the full end-of-session routine (session log write, `index.md`/`policy.md` review, persona evolution check, skill evolution check, unregistered persona detection) without requiring the user to describe it each time.
- Bumped control-plane version from `2.4` to `2.5`. Existing projects running `memory-seed update` will receive the updated `agent-rules.md`, `project-bootstrap.md`, and all skill files. The new `.agents/` templates and `copywriter-conversion.md` skill are added to projects that do not yet have them.

## 2.4.0 - 2026-06-04

- Added Codex CLI to MCP auto-registration. `memory-seed init` and `update` now write the `memory-seed-mcp` stdio server into a project-scoped `.codex/config.toml` (`[mcp_servers.memory-seed]`), bringing Codex to parity with Claude Code, Cursor, and Gemini. The merge is a zero-dependency text upsert (stdlib `tomllib` only inspects state; writes are line-based) so existing `.codex/config.toml` content and comments are preserved. Codex loads project MCP config only for **trusted** directories, so the trust step is surfaced in the README, the `--codex` retrieval-hook reminder, and a new `doctor` warning.
- Fixed Claude Code MCP registration: the server is now written to a project-root `.mcp.json` (the location Claude Code actually reads) instead of `.claude/settings.json > mcpServers`, which Claude Code silently ignored across 2.2.0–2.3.0. `memory-seed update` migrates existing projects by writing `.mcp.json` and stripping the dead `settings.json` block (ours-only; a foreign server squatting the key is left untouched).
- Added a non-fatal `warnings` channel to `doctor` / `DoctorResult`. It classifies the Codex MCP entry as `absent`, `current`, `foreign`, `stale-fixable`, or `stale-manual`, and warns when Codex hooks are installed without a working MCP registration — including when a hand-written non-standard TOML form is outdated and cannot be auto-migrated, so the no-op is never silent.
- Reframed the session-log format in `agent-rules.md` so the single-decision **DRAFT** record is the baseline shape, with the bare summary (simpler) and multi-decision (richer) shapes presented as explicit down/up routes. D/R are marked `(mandatory)` and A/F/T `(optional)`.
- Bumped control-plane version from `2.3` to `2.4` so existing projects running `memory-seed update` receive the reframed `agent-rules.md` and the Codex hook/MCP changes.

## 2.3.0 - 2026-05-29

- Made `memory-seed update` forward-only: it now skips a control-plane file when the project's local `memory-system-version` is the current version **or newer**, instead of only when it is exactly equal. Previously the equality check was symmetric, so a stale installed tool (older control-plane version) running `update` against a project on a newer control plane would silently overwrite the newer files with its older bundled seed — a downgrade. Version comparison is numeric, so multi-digit versions order correctly (`2.10` > `2.9`).
- Reframed the session-log append rule in `agent-rules.md` to be vendor-neutral. It now states the invariant ("append each entry at the physical end of the file; never insert above an existing entry") and the anchor hazard, with the mitigation that applies to any agent (confirm the actual last line before appending; never reuse a remembered anchor). `>>` / `open(f, 'a')` is demoted from a mandate to an optional technique for shell-capable agents, with a UTF-8 encoding caveat (some shells, e.g. PowerShell `>>`, default to other encodings, which would corrupt a UTF-8 log). The previous wording mandated a shell-specific mechanism inside a contract meant for any file-reading agent — and its heredoc example was unsafe on Windows. The `session-log-check.py` order-warning was reframed to match.
- Restored the two-step skill-registry wording in the `AGENTS.md` operating-mode read order ("Read `skills/index.md` as the deterministic skill trigger registry" / "Load full files only when the trigger registry matches"). It had been condensed to a single line that dropped the registry concept, diverging from `agent-rules.md`, `skills/index.md`, and `project-bootstrap.md`, which all describe the same two-step lazy-load contract.
- Bumped control-plane version from `2.2` to `2.3` so existing projects running `memory-seed update` receive the reframed append rule and the restored `AGENTS.md` wording.

## 2.2.3 - 2026-05-29

- Hardened session-log append discipline in `agent-rules.md`: added an explicit rule to use `>>` shell redirection or Python append mode (`open(f, 'a')`) when writing session entries, instead of editor replace/insert operations. Replace/insert requires an anchor line; if a prior edit already added content after that anchor, the entry lands mid-file. Append mode writes to the physical end unconditionally.
- Updated the session-log order-warning in `session-log-check.py` to include a concrete repair instruction: use `>>` or Python append mode to move an out-of-order entry to the end with the current clock time.
- Bumped control-plane version from `2.1` to `2.2`. Existing projects running `memory-seed update` will receive the updated `agent-rules.md`.

## 2.2.2 - 2026-05-29

- Fixed MCP server auto-registration to use `uvx --from memory-seed memory-seed-mcp --stdio` instead of the bare `memory-seed-mcp --stdio` command. The bare command requires `~/.local/bin` to be on the agent's PATH, which Claude Code and other agents do not inherit. Using `uvx --from memory-seed` resolves the script through uv, which is on system PATH, and works on any machine regardless of how or where the package is installed.

## 2.2.1 - 2026-05-29

- Bumped the reusable control-plane version from `2.0` to `2.1`. Existing projects running `memory-seed update` will now receive the updated `agent-rules.md` (DRAFT format improvements from 2.2.0) and `project-bootstrap.md`.

## 2.2.0 - 2026-05-29

- `memory-seed init` and `update` now register the `memory-seed-mcp --stdio` server in each vendor's MCP config: `.claude/settings.json` (Claude Code), `.cursor/mcp.json` (Cursor), and `.gemini/settings.json` (Gemini CLI). The `memory_search` and `memory_get_chunk` tools are now available to the agent without manual configuration.
- The memory-retrieval hook (`memory-retrieval-check.py`) now detects whether `memory-seed-mcp` is on PATH at prompt time. If the binary is missing (e.g. after a `uvx memory-seed init` ephemeral run), the hook surfaces a clear install instruction (`uv tool install memory-seed`) instead of directing the agent to call a tool that isn't available.
- All vendor config merge functions are now upsert (update-or-insert) instead of add-only. If a hook command or MCP entry changes between package versions, `memory-seed update` replaces the stale entry in place rather than appending a duplicate alongside it. Hook entries are identified by script filename (stable across version bumps); MCP entries are identified by command name.
- Consolidated the four direct session-log hook functions into thin wrappers over the shared `_merge_grouped_hook` / `_merge_cursor_event_hook` helpers, so there is one upsert implementation per schema shape.
- Promoted the DRAFT decision-record format definition in `agent-rules.md`: the "Reason Rules" section (naming and defining DRAFT) now precedes the "Entry Shapes" worked examples, so agents read the format definition before encountering it in use.
- Clarified that T (Tests/validation) may appear inline as `- T:` or as a separate `### Validation` section — both are accepted.
- Embedded DRAFT label reminder in the session-log staleness hook and the memory-retrieval hook so agents see the format at session start and at the moment of writing. Labels are now consistently tagged: `D (Decision, required), R (Reason, required), A (Alternatives, optional), F (Files, optional), T (Tests, optional)`.

## 2.1.3 - 2026-05-27

- Renamed the decision-record term "rationale" to "reason" across the reusable control-plane docs (`agent-rules.md`, `project-bootstrap.md`, `skills/memory_consolidation.md`). The DRAFT mnemonic is unchanged — `R` now stands for Reason — making the slot plainer and easier to recall.
- Documented the agent lifecycle hooks in the README: a new "Agent Hooks" section covering the session-log and memory-retrieval reminders installed for Claude Code, Codex, Gemini, and Cursor, plus `.memory-seed/hooks/` in the seed and runtime file trees.

## 2.1.2 - 2026-05-27

- Enforced append-only session-log chronology in `agent-rules.md`: entries are appended at the end with the current clock time, never backdated or reordered, so file order always matches timestamp order.
- Extended the session-log Stop hook (`session-log-check.py`) to warn when the day's entries are out of ascending time order, independent of the staleness check.
- Added a memory-retrieval hook (`memory-retrieval-check.py`) installed for all agents — Claude Code and Codex/Gemini via `UserPromptSubmit`, Cursor via `sessionStart` — reminding the agent to retrieve prior context (`memory_search` or recent session files) before substantive work. Gated by an 8-hour marker file so it fires about once per working session.
- Made MCP recency clock-sourced: `memory_search` now reads the current date from the system clock at call time and no longer accepts a caller-supplied `today` override (removed from the tool schema), so a stale agent-supplied date can no longer skew recency.

## 2.1.1 - 2026-05-27

- Fixed the Claude Code `Stop` hook output in `session-log-check.py`: now emits `{"systemMessage": ...}` instead of `hookSpecificOutput` with `hookEventName: "Stop"`, which failed Claude Code's hook output schema validation (`hookSpecificOutput` is only valid for `PreToolUse`, `UserPromptSubmit`, `PostToolUse`, and `PostToolBatch`).
- Added a `memory-seed help` command that prints the full command reference plus a "Keeping Memory Seed current" note distinguishing package upgrade from project seed-file update. Running `memory-seed` with no command now prints help instead of erroring.
- Documented the distinction between upgrading the package (`uv tool upgrade` / `pip install --upgrade`) and propagating seed files into a project (`memory-seed update`) in a new README "Updating" section; clarified that `update` sources files from the installed package, not PyPI.

## 2.1.0 - 2026-05-27

- Added multi-agent session log hooks: `memory-seed init` now installs `Stop`/after-response hooks for Claude Code (`.claude/settings.json`), Codex CLI (`.codex/hooks.json`), Cursor (`.cursor/hooks.json`), and Gemini CLI (`.gemini/settings.json`). Hooks remind the active agent to write a session log entry if none has been updated in the last 15 minutes.
- Added `memory_seed/seed/.memory-seed/hooks/session-log-check.py` — cross-platform Python hook script with `--codex`, `--cursor`, and `--gemini` flags for agent-specific output formats.
- Agent hook configs are handled as JSON merge targets (not seed file copies) so existing agent configuration is preserved on init and update.
- Strengthened `agent-rules.md` "End Of Turn" section: all agents (Claude, Codex, Gemini, Cursor) are now explicitly required to write session log entries before the current turn ends, not deferred or batched.
- Fixed `doctor()` to skip version-check for non-Markdown seed files.
- Added `.memory-seed/skills/index.md` as a deterministic skill trigger registry for universal lazy-loaded skills.
- Updated MCP memory retrieval to default to entry-level chunks using session YAML `entry_id`, with optional section granularity for narrower searches.
- Added control-plane guidance for sub-project runtime creation and parent/root coordination summaries without mirroring sub-project logs.
- Expanded operating-mode guidance for MCP history retrieval, unresolved history/current-file conflicts, public memory hygiene, and v2 guardrails.
- Clarified `uvx` one-off usage versus persistent `uv tool install`, project dependencies, and virtual-environment installs.

## 2.0.0 - 2026-05-25

- Promoted `.memory-seed/` as the canonical runtime directory with `agent-rules.md`, `project-bootstrap.md`, `index.md`, `policy.md`, lazy-loaded `skills/`, dated `sessions/`, and `archive/`.
- Added nearest-runtime discovery so nested sub-project folders can own isolated local memory state.
- Kept `.AGENTS/` as a code-level legacy fallback for older projects, but removed it from the v2 seed layout.
- Updated compact and MCP session extraction to use the discovered runtime boundary.
- Added default skill runbooks for security triage, data architecture, and local compilation.

## 1.6.1 - 2026-05-19

- Documented `uvx --from memory-seed` as the default way to run CLI and MCP commands without a global install.
- Clarified the difference between the Python package version and reusable control-plane version.
- Clarified that `memory-seed init` copies only Markdown seed files into target projects, not MCP server code or Python modules.

## 1.6.0 - 2026-05-19

- Added the local semantic cache core for heading-aware Markdown memory chunking, deterministic lexical ranking, optional embedding integration, and recency scoring.
- Added the lightweight stdio MCP server with `memory_search` and `memory_get_chunk` tools.
- Added `memory-seed-mcp-validate` for human-validatable search and fetch testing.
- Added support for timestamped session headings while keeping date-only session filenames.

## 1.5.3 - 2026-05-18

- Marked the project as beta maturity in package metadata.

## 1.5.2 - 2026-05-18

- Updated GitHub Actions workflow actions for Node.js 24 compatibility.

## 1.5.1 - 2026-05-18

- Prepared a patch release after the `1.5.0` PyPI release was already published.

## 1.5.0 - 2026-05-18

- Added the `memory-seed compact` command for summarizing recent session logs.
- Documented consolidation behavior and agent-led promotion of durable facts.

## Earlier

- Added reusable seed installation and update commands.
- Added project bootstrap instructions for generating `.AGENTS/index.md`, `.AGENTS/context.md`, `.AGENTS/style.md`, and dated session logs.
- Added doctor/version checks for reusable control-plane files.
