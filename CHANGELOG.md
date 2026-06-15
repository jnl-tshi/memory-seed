# Changelog

All notable changes to Memory Seed are summarized here.

## Unreleased

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

- **Non-destructive routing into pre-existing entry-point files.** The four routing files Memory Seed manages â€” `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` â€” share their names with files other tools own (e.g. HyperFrames also uses `AGENTS.md`/`CLAUDE.md`). `init` and `update` now decide per file by ownership: a file that doesn't exist is written in full (unchanged); a file carrying our `memory-system-version` frontmatter is version-gated and archived+replaced (unchanged); a **foreign** file (no frontmatter) has a marker-delimited routing block â€” `<!-- BEGIN memory-seed -->â€¦<!-- END memory-seed -->` pointing into `.memory-seed/` â€” **injected at the end, never overwriting the host's content** (even under `init --force`). On later updates the block is re-synced *in place* (the "second merge"), gated on content-equality so an unchanged stanza causes no churn. This mirrors the existing JSON-config merge philosophy (`_merge_grouped_hook`, the Copilot prompt-hook marker).
- **Behavior change:** a versionless entry-point file is now *merged* rather than *overwritten*. This retires the legacy "unversioned â†’ archive under `unknown-*` + clobber" upgrade path. The fail-safe direction: when ownership can't be proven from frontmatter, append a block rather than destroy a file that is most likely host-owned or hand-edited.
- Added a `doctor` route-presence backstop (non-fatal `warnings` channel): if a `.memory-seed/` runtime exists but a present entry-point file is foreign and carries no routing block, it is flagged as an orphaned runtime ("`AGENTS.md` does not route into the `.memory-seed/` runtime â€” run `memory-seed update`"). Foreign routing files are no longer reported as version mismatches (the host owns the file; Memory Seed only manages its injected block).
- Bumped control-plane version from `2.7` to `2.8`. Existing projects running `memory-seed update` get the routing-merge behavior; a project whose `AGENTS.md`/`CLAUDE.md` is owned by another tool keeps that content and gains the routing block.

## 2.7.0 - 2026-06-14

- Promoted three **baseline seed additions**. Two new universal skill runbooks ship with `init`: `document_ingestion.md` (reading `.docx`/`.pdf`/`.pptx`/`.xlsx`/`.csv`/images as Markdown via markitdown, with per-format routing and fidelity caveats) and `office_document_editing.md` (field-safe surgical editing of Office documents that contain citations, captions, cross-references, or a TOC). Both get trigger-registry entries in `skills/index.md`. A new **Working Principles** section in `agent-rules.md` adds three cross-cutting rules: POC-gate a risky automated method before scaling it, state the verification split (what the agent can verify vs. what only the user can), and read share-aware copies of locked files.
- Added an **orphan & dead-artifact sweep** to the end-of-session routine. The "End Of Turn" section of `agent-rules.md` (and its seed twin, mirrored in this repo's `/esr` command) now includes a diff-scoped step: for everything the session added, confirm it is referenced somewhere (imported / registered / linked / routed) or remove it; for everything deleted or renamed, search for and resolve dangling references; flag scratch debris (temp files, commented-out code, half-removed features, stray untracked dirs, `*.bak`). The step is language-agnostic and never installs tools â€” if the project already declares a dead-code tool (vulture/ruff, knip, ArchUnit, cppcheck) the agent may run it, otherwise it just notes one is available. The sweep reliably catches orphan *files and features*; whole-codebase *dead code* remains a periodic tool job, stated explicitly so the routine does not over-promise.
- Added a deterministic **orphan-skill check** to `memory-seed doctor` (non-fatal `warnings` channel): any `.memory-seed/skills/*.md` runbook not registered in `skills/index.md` is flagged so it gets a trigger entry or is removed. This is the automatable backstop to the agent-performed sweep; it has deterministic ground truth and no false positives. (A session-log dangling-reference scan was deliberately *not* added â€” logs legitimately cite renamed, deleted, or example paths.)
- Bumped control-plane version from `2.6` to `2.7`. Existing projects running `memory-seed update` receive the updated `agent-rules.md` and `memory_doctor.md` skill.

## 2.6.0 - 2026-06-13

- Added **agent-selective install**. `memory-seed init` now accepts `--agents claude,codex` (and prompts interactively on a terminal) to install only the chosen agents' files â€” keeping repos clean (e.g. no `GEMINI.md` for a Claude+Codex user). `AGENTS.md`, the `.memory-seed/` runtime, and `.agents/` personas are always installed; only agent-specific routing files and per-agent hook/MCP configs are gated. The choice is persisted in `.memory-seed/project.yaml` (`agents:` list), which `doctor` and `update` respect (a deselected agent is never flagged missing or re-added). A project with no `project.yaml` behaves exactly as before (all agents). Added `memory-seed agents list|add|remove <agent>`; `remove` strips only Memory Seed's own entries (foreign config preserved) and backs up everything it touches. `codex` and `cursor` get no routing file â€” they read `AGENTS.md` natively.
- Added a **SessionStart orientation hook** (`session-start-context.py`). It reads the newest dated `.memory-seed/sessions/*.md` file directly and injects its path, all entry headings, and the most recent entry's body at session start, so agents establish current state by recency rather than semantic search (which ranks by topical similarity and can bury or omit the newest entry). Wired to Claude/Codex `SessionStart`, Gemini `SessionStart`, and Cursor `sessionStart` via `init`/`update`.
- Added **GitHub Copilot** as a supported agent. Copilot CLI: repo-local `.github/mcp.json` (`mcpServers` key, `type: stdio`) for `memory_search`/`memory_get_chunk`, plus a `sessionStart` **prompt** hook in `.github/hooks/memory-seed.json` (Copilot command hooks cannot inject context at sessionStart, and its `userPromptSubmitted`/`agentStop`/`sessionEnd` events do not support `additionalContext`, so it receives no per-turn reminders). VS Code Copilot: `.vscode/mcp.json` (`servers` key) + a thin `.github/copilot-instructions.md` router. The Copilot coding agent (github.com) reads `AGENTS.md` already; its MCP lives in repo/org settings (manual).
- **Fixed dead Gemini hook wiring.** Earlier versions wired Gemini's session-log and retrieval hooks to `Stop`/`UserPromptSubmit`, events Gemini does not expose, so they never fired. They now target `AfterAgent` (turn-end) and `BeforeAgent` (prompt-submit); `memory-seed update` strips the stale entries. The `--gemini` hook output now uses `hookSpecificOutput.additionalContext` as Gemini requires.
- Reconciled the per-prompt retrieval reminder (`memory-retrieval-check.py`) with the recency rule: it now points at `memory_search` for **topical** recall and defers "what's the latest" to the SessionStart/newest-file path, matching the new "Recency vs. Topical Retrieval" section in `agent-rules.md`.
- Bumped control-plane version from `2.5` to `2.6`. Existing projects running `memory-seed update` receive the new SessionStart hook, the Copilot wiring, the Gemini hook migration, and the reconciled reminder.

## 2.5.0 - 2026-06-04

- Added `.agents/` persona library. `memory-seed init` now ships six vendor-neutral agent persona templates (developer, content-creator, researcher, sales-rep, solo-founder, copywriter) under `.agents/`. Each persona file defines an identity, memory protocol pointing at `.memory-seed/`, operating rules, session discipline, skill routing, and an append-only `## Project Adaptations` section for traceable persona evolution. Persona files are runtime-local (deploy-once; `memory-seed update` never overwrites them) so project-specific customisations survive upgrades.
- Added `agent_name` field to session log entries. A new optional YAML field (`agent_name: <persona-slug>`) sits alongside the existing `agent_type` (LLM model/vendor) in every session entry. `memory_search` parses and returns it, enabling per-persona history queries. Old entries without the field are unaffected.
- Expanded `project-bootstrap.md` Step 9 â€” persona activation is now a five-sub-step guided flow: persona selection, personalization (entity name via pop-culture pick or user input; user name inferred from `git config`; business name inferred from project files with placeholders replaced in-file), skill routing (mapped skills table filled per persona role; gap detection with draft â†’ approval â†’ write for missing skills), `_registry.yaml` write with resolved metadata, and automatic onboarding of any unregistered `.agents/*.md` files dropped in after init.
- Expanded `agent-rules.md` Operating Mode Start with Step 9: if `.agents/_registry.yaml` exists, read it, load all active persona files, apply rules alongside `agent-rules.md` and `policy.md`, and record `agent_name` in all session entries. Expanded end-of-turn with Step 8: skill evolution â€” if a repeating workflow gap emerged, propose a draft skill file for user approval, then write it to `.memory-seed/skills/`, add a `persona:` trigger entry to `skills/index.md`, and update the persona's `### Role-Specific Skills` section.
- Added `copywriter-conversion.md` skill to the seed. Ships as a first-class universal skill with framework-selection decision table (AIDA, PAS, BAB, FAB, 4Ps, JTBD keyed to audience awareness level), developer-tool objection map, and format templates for README hero, landing page, Product Hunt tagline, email subject line, and GitHub description. Trigger entry in `skills/index.md` includes a `persona: copywriter` field; agents respect this and skip the skill when the copywriter persona is not active.
- Added `skills/index.md` trigger entries now support an optional `persona:` field scoping a skill to a specific active persona. Agents skip persona-scoped skills when the named persona is not active.
- Added bidirectional Didion â†” Hopkins handoff protocol. A `## VII. Handoff Protocol` section in both the content-creator and copywriter persona templates defines a structured Copy Brief (Didion â†’ Hopkins) and Repurposing Note (Hopkins â†’ Didion) appended to the session log for the other persona to consume at startup. Neither persona reviews the other's work before publishing; Stark (solo-founder) holds the shipping decision.
- Added ESR slash command. `.claude/commands/esr.md` registers `/esr` in Claude Code, triggering the full end-of-session routine (session log write, `index.md`/`policy.md` review, persona evolution check, skill evolution check, unregistered persona detection) without requiring the user to describe it each time.
- Bumped control-plane version from `2.4` to `2.5`. Existing projects running `memory-seed update` will receive the updated `agent-rules.md`, `project-bootstrap.md`, and all skill files. The new `.agents/` templates and `copywriter-conversion.md` skill are added to projects that do not yet have them.

## 2.4.0 - 2026-06-04

- Added Codex CLI to MCP auto-registration. `memory-seed init` and `update` now write the `memory-seed-mcp` stdio server into a project-scoped `.codex/config.toml` (`[mcp_servers.memory-seed]`), bringing Codex to parity with Claude Code, Cursor, and Gemini. The merge is a zero-dependency text upsert (stdlib `tomllib` only inspects state; writes are line-based) so existing `.codex/config.toml` content and comments are preserved. Codex loads project MCP config only for **trusted** directories, so the trust step is surfaced in the README, the `--codex` retrieval-hook reminder, and a new `doctor` warning.
- Fixed Claude Code MCP registration: the server is now written to a project-root `.mcp.json` (the location Claude Code actually reads) instead of `.claude/settings.json > mcpServers`, which Claude Code silently ignored across 2.2.0â€“2.3.0. `memory-seed update` migrates existing projects by writing `.mcp.json` and stripping the dead `settings.json` block (ours-only; a foreign server squatting the key is left untouched).
- Added a non-fatal `warnings` channel to `doctor` / `DoctorResult`. It classifies the Codex MCP entry as `absent`, `current`, `foreign`, `stale-fixable`, or `stale-manual`, and warns when Codex hooks are installed without a working MCP registration â€” including when a hand-written non-standard TOML form is outdated and cannot be auto-migrated, so the no-op is never silent.
- Reframed the session-log format in `agent-rules.md` so the single-decision **DRAFT** record is the baseline shape, with the bare summary (simpler) and multi-decision (richer) shapes presented as explicit down/up routes. D/R are marked `(mandatory)` and A/F/T `(optional)`.
- Bumped control-plane version from `2.3` to `2.4` so existing projects running `memory-seed update` receive the reframed `agent-rules.md` and the Codex hook/MCP changes.

## 2.3.0 - 2026-05-29

- Made `memory-seed update` forward-only: it now skips a control-plane file when the project's local `memory-system-version` is the current version **or newer**, instead of only when it is exactly equal. Previously the equality check was symmetric, so a stale installed tool (older control-plane version) running `update` against a project on a newer control plane would silently overwrite the newer files with its older bundled seed â€” a downgrade. Version comparison is numeric, so multi-digit versions order correctly (`2.10` > `2.9`).
- Reframed the session-log append rule in `agent-rules.md` to be vendor-neutral. It now states the invariant ("append each entry at the physical end of the file; never insert above an existing entry") and the anchor hazard, with the mitigation that applies to any agent (confirm the actual last line before appending; never reuse a remembered anchor). `>>` / `open(f, 'a')` is demoted from a mandate to an optional technique for shell-capable agents, with a UTF-8 encoding caveat (some shells, e.g. PowerShell `>>`, default to other encodings, which would corrupt a UTF-8 log). The previous wording mandated a shell-specific mechanism inside a contract meant for any file-reading agent â€” and its heredoc example was unsafe on Windows. The `session-log-check.py` order-warning was reframed to match.
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
- Clarified that T (Tests/validation) may appear inline as `- T:` or as a separate `### Validation` section â€” both are accepted.
- Embedded DRAFT label reminder in the session-log staleness hook and the memory-retrieval hook so agents see the format at session start and at the moment of writing. Labels are now consistently tagged: `D (Decision, required), R (Reason, required), A (Alternatives, optional), F (Files, optional), T (Tests, optional)`.

## 2.1.3 - 2026-05-27

- Renamed the decision-record term "rationale" to "reason" across the reusable control-plane docs (`agent-rules.md`, `project-bootstrap.md`, `skills/memory_consolidation.md`). The DRAFT mnemonic is unchanged â€” `R` now stands for Reason â€” making the slot plainer and easier to recall.
- Documented the agent lifecycle hooks in the README: a new "Agent Hooks" section covering the session-log and memory-retrieval reminders installed for Claude Code, Codex, Gemini, and Cursor, plus `.memory-seed/hooks/` in the seed and runtime file trees.

## 2.1.2 - 2026-05-27

- Enforced append-only session-log chronology in `agent-rules.md`: entries are appended at the end with the current clock time, never backdated or reordered, so file order always matches timestamp order.
- Extended the session-log Stop hook (`session-log-check.py`) to warn when the day's entries are out of ascending time order, independent of the staleness check.
- Added a memory-retrieval hook (`memory-retrieval-check.py`) installed for all agents â€” Claude Code and Codex/Gemini via `UserPromptSubmit`, Cursor via `sessionStart` â€” reminding the agent to retrieve prior context (`memory_search` or recent session files) before substantive work. Gated by an 8-hour marker file so it fires about once per working session.
- Made MCP recency clock-sourced: `memory_search` now reads the current date from the system clock at call time and no longer accepts a caller-supplied `today` override (removed from the tool schema), so a stale agent-supplied date can no longer skew recency.

## 2.1.1 - 2026-05-27

- Fixed the Claude Code `Stop` hook output in `session-log-check.py`: now emits `{"systemMessage": ...}` instead of `hookSpecificOutput` with `hookEventName: "Stop"`, which failed Claude Code's hook output schema validation (`hookSpecificOutput` is only valid for `PreToolUse`, `UserPromptSubmit`, `PostToolUse`, and `PostToolBatch`).
- Added a `memory-seed help` command that prints the full command reference plus a "Keeping Memory Seed current" note distinguishing package upgrade from project seed-file update. Running `memory-seed` with no command now prints help instead of erroring.
- Documented the distinction between upgrading the package (`uv tool upgrade` / `pip install --upgrade`) and propagating seed files into a project (`memory-seed update`) in a new README "Updating" section; clarified that `update` sources files from the installed package, not PyPI.

## 2.1.0 - 2026-05-27

- Added multi-agent session log hooks: `memory-seed init` now installs `Stop`/after-response hooks for Claude Code (`.claude/settings.json`), Codex CLI (`.codex/hooks.json`), Cursor (`.cursor/hooks.json`), and Gemini CLI (`.gemini/settings.json`). Hooks remind the active agent to write a session log entry if none has been updated in the last 15 minutes.
- Added `memory_seed/seed/.memory-seed/hooks/session-log-check.py` â€” cross-platform Python hook script with `--codex`, `--cursor`, and `--gemini` flags for agent-specific output formats.
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
