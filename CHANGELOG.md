# Changelog

All notable changes to Memory Seed are summarized here.

## Unreleased

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
