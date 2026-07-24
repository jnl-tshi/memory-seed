# Memory Seed

[![PyPI](https://img.shields.io/pypi/v/memory-seed.svg)](https://pypi.org/project/memory-seed/)
[![Python](https://img.shields.io/pypi/pyversions/memory-seed.svg)](https://pypi.org/project/memory-seed/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Publish to PyPI](https://github.com/jnl-tshi/memory-seed/actions/workflows/publish.yml/badge.svg)](https://github.com/jnl-tshi/memory-seed/actions/workflows/publish.yml)
[![Verify](https://github.com/jnl-tshi/memory-seed/actions/workflows/verify.yml/badge.svg)](https://github.com/jnl-tshi/memory-seed/actions/workflows/verify.yml)
[![CodeQL](https://github.com/jnl-tshi/memory-seed/actions/workflows/codeql.yml/badge.svg)](https://github.com/jnl-tshi/memory-seed/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/jnl-tshi/memory-seed/badge)](https://scorecard.dev/viewer/?uri=github.com/jnl-tshi/memory-seed)

Memory Seed is a portable local memory system for AI coding agents. It plants a small Markdown control plane into a project so agents can recover project purpose, conventions, risks, decisions, and recent work without depending on vendor-hosted memory.

It is built first for solo developers who move between Codex, Claude Code, Gemini CLI, and other file-reading agents. Teams can also use it to standardize local agent memory across repositories without introducing a database or hosted memory service.

**Highlights**

- **Local-first, Git-native.** Memory is plain Markdown in your repository - versioned, diffable, greppable, and yours. No database, no hosted service, no telemetry.
- **Vendor-neutral.** One control plane serves Claude Code, Codex, Gemini CLI, Cursor, and Copilot; switching agents keeps the memory.
- **Inspectable decisions, not summaries.** Append-only session logs record decisions with reasons (DRAFT records), typed lifecycle edges (`replaces`/`evolves`), artifact lineage, and commit links - validated by `links check`.
- **Agent-native retrieval.** MCP `memory_search`/`memory_get_chunk` give ranked, self-contained memory chunks with computed freshness status; hooks keep agents oriented at session start.
- **Safe collaboration.** Branch-aware session fusing (`session merge-branch`) integrates multi-agent work with chronology and provenance enforced.

> **Treat `.memory-seed/` as publishable.** Session logs travel with the repository - see
> [Public Memory Hygiene](#public-memory-hygiene) before pushing memory to a public remote.

## Demo

https://github.com/user-attachments/assets/b1c64d9e-4a67-4bc2-a030-d8ba7f17ccfe

[Watch the 30-second demo](https://github.com/jnl-tshi/memory-seed/releases/download/v2.1.3/memory-seed-demo.mp4) if the player above does not load.

## Quickstart

From the root of a project where you want local agent memory:

```powershell
uvx --from memory-seed memory-seed init --dry-run
uvx --from memory-seed memory-seed init
```

Then ask your coding agent to read `AGENTS.md` and follow nearest-runtime discovery. The project receives a seeded `.memory-seed/` control plane:

```text
.memory-seed/
  agent-rules.md
  project-bootstrap.md
  skills/
  sessions/
  archive/
```

The first bootstrap pass generates `.memory-seed/index.md` and `.memory-seed/policy.md` from local inspection and user answers.

For an existing project that already has Memory Seed:

```powershell
uvx --from memory-seed memory-seed update --dry-run
uvx --from memory-seed memory-seed update
```

For agent-native memory search over MCP:

```json
{
  "command": "uvx",
  "args": ["--from", "memory-seed", "memory-seed-mcp", "--stdio"]
}
```

Validate the search workflow manually:

```powershell
uvx --from memory-seed memory-seed-mcp-validate "bootstrap mode check"
```

## How It Works

1. `memory-seed init` plants the reusable control plane: `AGENTS.md` routing, `.memory-seed/` rules/skills/hooks, and agent configs (hooks + MCP registration) for the agents you select.
2. Agents follow `AGENTS.md` to the nearest `.memory-seed/` runtime and read the small always-read set (rules, index, policy, skill registry); deeper skills lazy-load by trigger.
3. Work gets recorded as append-only, timestamped session entries with decisions and reasons; lifecycle hooks remind the agent to log and orient it at session start.
4. Retrieval is layered: recency comes from reading the newest session file directly, topical recall from MCP `memory_search` (semantic + lexical + recency ranking, local CPU-only embeddings).
5. **Memory Trace**, the optional companion UI, renders the same files read-only - search, timeline, graph, and Trail lineage views.

## See It Work

Visual proof (placeholders until real captures land):

- `[placeholder: screenshot - memory-seed init in a fresh project]`
- `[placeholder: screenshot - Memory Trace timeline/graph view]`

You can validate the local search workflow without configuring an agent client:

```powershell
uvx --from memory-seed memory-seed-mcp-validate "bootstrap mode check"
```

Representative output:

```text
# MCP Memory Validation

Query: bootstrap mode check

Top results:
1. .memory-seed/sessions/2026-05-25.md: v2 runtime migration started
   score=...
   heading=2026-05-17 - Bootstrap mode check fix

Fetched top chunk:
Source: .memory-seed/sessions/2026-05-25.md:...
Heading: 2026-05-17 - Bootstrap mode check fix
...
```

The validator performs the same search-then-fetch flow an MCP-capable agent uses: rank matching memory chunks, fetch the selected chunk by id, and print the exact source text for human review.

## Lightweight install (without semantic ranking)

`model2vec` is a **required** dependency and the default install includes it — semantic ranking is
part of the product, not an add-on. It is also the package's *only* required dependency, and it
downloads a ~59 MB model on first use.

If that download is unwanted — an air-gapped machine, a small container, CI that only exercises the
Markdown surface — install without it:

```powershell
python -m pip install --no-deps memory-seed
```

Everything still works: session logging, `links check`, `docs check`, fusing, the topic vocabulary
and the whole CLI. Only **ranking** changes — search falls back from semantic to lexical, and
`link audit` candidate scoring loses its strongest signal. Nothing errors, and nothing is hidden:
`memory-seed esr` reports the state on every run, as `DEGRADED — ranking is lexical only`.

Add it later with `python -m pip install model2vec`; nothing else needs reinstalling.

> Why `--no-deps` and not an extra: extras can only *add* dependencies, never subtract, so
> "memory-seed without semantic" cannot be expressed as one. Because `model2vec` is the sole
> required dependency, `--no-deps` is exactly equivalent — an invariant pinned by
> `test_model2vec_is_the_only_required_dependency`, so adding a second required dependency fails
> the suite rather than silently breaking this path.

## Memory Trace (optional review UI)

**Memory Trace** is the optional local browser UI for exploring a project's Memory Seed runtime: read-only search, filters, timeline, graph, and reader/details views over your Markdown session files, backed by a rebuildable local SQLite cache outside the repository. It ships inside the main `memory-seed` distribution so there is one installable product, while the web dependencies stay behind the `trace` extra so plain `pip install memory-seed` remains lightweight.

Install the review UI with the optional extra:

```powershell
python -m pip install "memory-seed[trace]"
memory-trace --cwd . --host 127.0.0.1 --port 8765 --no-open
```

To open both the vanilla and React versions from one local server, run:

```powershell
memory-trace --cwd . --host 127.0.0.1 --port 8770 --open-both
```

For this source checkout on Windows, `.\scripts\launch-memory-trace.ps1` supplies the local
`PYTHONPATH`, reuses a healthy Trace server already on its requested port, and opens `/` plus `/next`.

For `uv` tool installs, install the owning package with the extra. To add Trace
to an existing core-only tool install, reinstall the tool with `--force`:

```powershell
uv tool install "memory-seed[trace]"
uv tool install --force "memory-seed[trace]"
```

The Trail view renders session entries as a git-graph-style timeline: branch lanes from recorded `branch:` metadata, fork/merge connectors driven by the `Memory-Entry:` commit trailers where they exist (with an "estimated" positional fallback for older history), clickable trunk merge rings, typed `replaces`/`evolves` lifecycle routes, and an on-device **worktree switcher** so one running server can show each checkout's branch-specific memory. Asset `?v=` tags are content-hashed at serve time (no stale-browser-cache surprises), and `--static-root <path>` / `MEMORY_TRACE_STATIC_ROOT` serves another checkout's UI assets - useful for verifying a worktree's UI changes without copying files.

The former `memory-seed[lense]` extra and `memory-seed lense` command were a temporary alias kept for one
release window after the product renamed to Memory Trace; both were removed for the 2.20 release. Install
`memory-seed[trace]` and run `memory-trace` instead. Without the `trace` extra installed, `memory-trace`
prints an install hint instead of failing with a Python traceback.

## Why This Exists

AI coding agents are useful, but their project context is fragile. They forget decisions between sessions, vendor memory is not portable, and stuffing full history into prompts wastes context.

Memory Seed keeps the durable memory layer local, inspectable, and boring on purpose:

- Markdown files live with the project.
- Tool-specific entry files route into the nearest `.memory-seed/` runtime.
- Generated project memory stays separate from reusable seed files.
- Session logs capture what changed and why.
- MCP search lets agents retrieve precise historical context without reading every log.

The result is a lightweight memory workflow you can understand, commit, review, copy, and repair.

## Goals

- Keep project memory local, inspectable, and portable.
- Support file-reading AI coding agents through predictable Markdown files.
- Route tool-specific entry files into the nearest `.memory-seed/` runtime.
- Support nested sub-project runtimes with local active state and local skills.
- Keep policy separate from functional runbooks.
- Archive reusable control-plane versions while keeping generated project memory outside version archives.

## Agent Support

| Agent or client | Support path |
| --- | --- |
| Codex | Starts from `AGENTS.md`; MCP server auto-registered in `.codex/config.toml` (loads once the project directory is trusted). |
| Claude Code | Starts from `CLAUDE.md`; MCP server auto-registered via `uvx --from memory-seed`. |
| Gemini CLI | Starts from `GEMINI.md`; MCP server auto-registered in `.gemini/settings.json`. |
| Cursor | Starts from `AGENTS.md`; MCP server auto-registered in `.cursor/mcp.json`. |
| GitHub Copilot | CLI starts from `AGENTS.md`; MCP auto-registered in `.github/mcp.json` (`mcpServers` key). VS Code via `.vscode/mcp.json` (`servers` key) + a thin `.github/copilot-instructions.md` router. The coding agent reads `AGENTS.md`; its MCP is configured in repo/org settings (manual). |
| Other file-reading agents | Start from `AGENTS.md` and follow nearest `.memory-seed/` runtime discovery. |
| MCP-capable clients | Use `memory_search` and `memory_get_chunk` through `memory-seed-mcp --stdio`. |

### Choosing which agents to install

Interactive `memory-seed init` asks which agent integrations should be installed, with every
supported agent selected by default so unused integrations can be opted out. Non-interactive init
keeps the backward-compatible default of all agents unless flags say otherwise:

```bash
memory-seed init --agents claude,codex     # only Claude + Codex artifacts
memory-seed init --agents none             # shared runtime only, no agent-specific configs
memory-seed init --no-agent-prompt          # skip the interactive agent prompt
memory-seed init                            # prompts on a terminal; all agents otherwise
```

`AGENTS.md`, the `.memory-seed/` runtime, and `.agents/` personas are always installed (they are
agent-agnostic). Only the agent-specific routing files (`CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md`) and per-agent hook/MCP configs are gated by the selection.
`codex` and `cursor` have no routing file - they read `AGENTS.md` natively.

The selection is persisted to `.memory-seed/project.yaml` (`agents:` list), which `doctor` and
`update` respect, so an unselected agent's files are never flagged missing or re-added. A
present-but-empty `agents:` block is the explicit zero-agent state; a project with no `project.yaml`
behaves as before (all agents). Init and `agents list` report both installed and ignored agents.
Reconfigure later:

```bash
memory-seed agents list           # show selected and ignored agents
memory-seed agents add gemini     # install an agent's files
memory-seed agents remove gemini  # back up + remove an agent's files (foreign config preserved)
```

### Choosing skill profiles

New projects install a minimal core skill set by default: session logging, history
retrieval, end-of-turn closeout, hygiene, risk signaling, doctor, consolidation,
and sub-project runtime guidance. Optional skills are installed by profile or
individual filename and are still lazy-loaded through `.memory-seed/skills/index.md`.

```bash
memory-seed init --profile coding,planning
memory-seed init --skills compact_mermaid_diagrams.md
memory-seed init --all-skills
memory-seed skills list
memory-seed skills ignored
memory-seed skills add planning
memory-seed skills add governance
memory-seed skills remove proposal_lifecycle.md
```

The selection is stored in `.memory-seed/project.yaml` under `skills.profiles`,
`skills.selected`, and `skills.ignored`. `memory-seed update` respects that state
and does not re-add ignored optional skills. The `planning` profile also creates
`docs/inbox/`, `docs/todo/`, `docs/todo/completed/`, and `docs/reference/`
`.gitkeep` anchors for the proposal workflow and its source/reference material.
The `governance` profile installs `skill_architecture.md` for projects that maintain
Memory Seed skills, trigger registries, profile boundaries, or seed/live control-plane parity.

## Agent Hooks

`memory-seed init` and `memory-seed update` install lifecycle hooks that keep memory current without relying on the agent to remember. Each hook is merged into the agent's own config file (existing settings are preserved), so it works regardless of which agent opens the project:

| Agent | Config file | Session-log reminder | Memory-retrieval reminder | Session-start orientation |
| --- | --- | --- | --- | --- |
| Claude Code | `.claude/settings.json` | `Stop` | `UserPromptSubmit` | `SessionStart` |
| Codex CLI | `.codex/hooks.json` | `Stop` | `UserPromptSubmit` | `SessionStart` |
| Gemini CLI | `.gemini/settings.json` | `AfterAgent` | `BeforeAgent` | `SessionStart` |
| Cursor | `.cursor/hooks.json` | `afterAgentResponse` | `sessionStart` | `sessionStart` |
| GitHub Copilot CLI | `.github/hooks/memory-seed.json` | — | — | `sessionStart` (prompt) |

Both reminders are cross-platform Python scripts in `.memory-seed/hooks/`:

- `session-log-check.py` - after a turn, reminds the agent to append a session-log entry if none was written in the last 15 minutes, and warns if the day's entries are out of ascending time order. When the per-user participant gate selects a user file, it checks only that user's grouped file (`sessions/YYYY-MM/YYYY-MM-DD/<user>.md`) so another contributor's recent entry does not suppress the reminder. The staleness check is anchored to the last logged entry's own timestamp, so it always eventually fires once 15 real minutes pass, independent of how many turns ran in between - what it cannot detect is whether a fired reminder was acted on. A gitignored state file (`.memory-seed/.session-log-check-state`, fail-open on corruption) tracks consecutive stale checks with no new entry appearing in between, so a reminder that goes unaddressed escalates to a louder, explicit "repeated" warning on the next check instead of repeating identically.
- `memory-retrieval-check.py` — before substantive work, reminds the agent to use `memory_search` for topical recall and to read the newest session file directly for current state. Gated by an 8-hour marker file so it fires about once per working session.
- `session-start-context.py` - at session start, first directs the agent to locate, read, and follow the nearest applicable `AGENTS.md`, then injects the five newest applicable session entries across the latest relevant files so project context comes from recency rather than semantic search. Each entry is context-capped and names its source file for a full direct read. With a configured user it reads that user's recent files and lists same-day co-contributor files by path and entry count; without a configured user it preserves legacy flat-file behavior. Empty/new projects still receive the `AGENTS.md` directive. Fires once per session for Claude, Codex, Gemini, and Cursor; Copilot CLI cannot run command hooks at session start, so it gets a static `prompt` hook with the same instructions instead.
- `prepare-commit-msg.py` - a **git** hook (not an agent hook): stamps one `Memory-Entry: <entry_id>` trailer per staged session entry onto ordinary commits, so the commit<->entry link is true by construction instead of relying on the author to remember. Scoped to session trees only, deduplicated, and it never blocks a commit. `memory-seed init` installs the shim into the git common dir (covering every worktree) when a repository exists; existing checkouts opt in with `memory-seed hooks install`. `memory-seed hooks status` reports missing, stale, broken, current, or foreign hook state; `memory-seed hooks repair` refreshes only missing or Memory Seed-managed hooks. A pre-existing foreign hook is reported, never overwritten. On Windows, the installed shim uses the active Python executable directly to avoid Git-for-Windows shell-startup failures.

The hooks nudge; they never block. The scripts use Python 3.11+, which Memory Seed already requires.

Beyond the hooks, the end-of-session routine in `agent-rules.md` ("End Of Turn") includes a diff-scoped **orphan & artifact sweep**: before closing a session the agent reviews what it changed, confirms new files/features are actually wired in, resolves references left dangling by deletions or renames, and flags scratch debris — so half-removed features and stray files are caught as they happen rather than accumulating. It is language-agnostic and never installs tooling; a project's own dead-code tool (vulture/ruff, knip, ArchUnit, cppcheck) can be run for deeper whole-codebase checks when one is already present.

The routine also runs a **consolidation review** (promote durable, reusable facts from the session logs into `index.md`/`policy.md` via the `memory_consolidation` skill) and a **baseline-promotion check** (flag any approved adaptation general enough to reuse beyond this project, recorded in `.memory-seed/plans/`). The mechanical half of the routine runs as one read-only command, `memory-seed esr` - links check, topics check, the session-scoped lifecycle link audit, per-worktree posture (merged+clean checkouts marked as stale-sweep candidates), and seed-twin drift - every section printing even when clean so a skipped step is visible. The whole routine ships as a seeded **`/esr`** command for the agents with a repo-level command mechanism: Claude (`.claude/commands/esr.md`) and Gemini (`.gemini/commands/esr.toml`); Codex, Cursor, and other agents run the same routine directly from `agent-rules.md`. There is intentionally no blocking end-of-turn hook — evolution needs reasoning and user approval, which a hook cannot do.

## Reusable Seed Files

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.claude/commands/esr.md
.gemini/commands/esr.toml
.github/copilot-instructions.md
.memory-seed/
  agent-rules.md
  project-bootstrap.md
  hooks/
    session-log-check.py
    memory-retrieval-check.py
    session-start-context.py
    prepare-commit-msg.py
  skills/
    index.md
    agent_collaboration.md
    code_search.md
    copywriter-conversion.md
    data_architecture.md
    document_ingestion.md
    end_of_turn.md
    history_retrieval.md
    local_compilation.md
    memory_consolidation.md
    memory_doctor.md
    memory_hygiene.md
    office_document_editing.md
    release_publishing.md
    security_triage.md
    session_logging.md
    subproject_runtime.md
  sessions/
  archive/
```

## Runtime Files

```text
.memory-seed/
  agent-rules.md
  project-bootstrap.md
  index.md
  policy.md
  hooks/
  skills/
  sessions/
  archive/
```

## Current Version

The current reusable control-plane version is `2.18`.

Legacy `.AGENTS/` projects remain supported as a fallback during migration.

## Skill Trigger Registry

`.memory-seed/skills/index.md` is the deterministic trigger registry for universal skills. Agents read it during startup, evaluate triggers in listed order, and lazy-load only the full skill runbooks that match the task.

Project and sub-project runtimes may override or disable inherited skills in their generated `index.md`. Parent skill registries apply only when inheritance is enabled and not locally overridden.

Sub-project runtimes keep detailed logs local. Parent/root memory should receive only brief coordination summaries when sub-project work changes parent-visible topology, shared design, release behavior, policy inheritance, dependencies, risks, or active priorities.

## Python CLI

Memory Seed includes a small Python CLI.

Use `uvx` for one-off execution. It runs Memory Seed in an isolated tool environment, so you do not need a global install and you avoid stale local commands:

```powershell
uvx --from memory-seed memory-seed doctor
uvx --from memory-seed memory-seed init --dry-run
uvx --from memory-seed memory-seed update --dry-run
uvx --from memory-seed memory-seed compact
uvx --from memory-seed memory-seed branch status
uvx --from memory-seed memory-seed ranking-ab --signal supersession_damping
uvx --from memory-seed memory-seed session merge-branch --branch <branch>
```

Use `uv tool install memory-seed` when you want Memory Seed installed persistently as a local machine tool with console scripts on PATH:

```powershell
uv tool install memory-seed
memory-seed doctor
memory-seed-mcp --stdio
memory-seed-mcp-validate "bootstrap mode check"
```

Use `uv add memory-seed` only when the current Python project itself depends on Memory Seed as a package:

```powershell
uv add memory-seed
```

Use `uv pip install memory-seed` when installing Memory Seed into the active virtual environment rather than as a standalone tool:

```powershell
uv pip install memory-seed
```

For repeatable team or production usage, pin the package version:

```powershell
uvx --from memory-seed==2.18.0 memory-seed doctor
uvx --from memory-seed==2.18.0 memory-seed update --dry-run
```

If you are not using uv, install or upgrade the CLI with pip:

```powershell
python -m pip install --upgrade memory-seed
python -m pip show memory-seed
```

`python -m pip show memory-seed` reports the installed Python package version, such as `2.18.0`. `memory-seed version` reports the reusable control-plane version, currently `2.18`; it is not the package-version check.

To discover commands and flags, use `memory-seed help` (also shown when you run `memory-seed` with no command), `memory-seed -h`, or `memory-seed <command> -h` for a specific command.

`memory-seed ranking-ab --signal <name> [--query <q> ...] [--json]` compares a named ranking signal
off versus on over the full live corpus. It reports directional ranking checks and unaffected-query
controls, exits `0` only when the gate passes, exits `1` for a regression or incomplete gate, and exits
`2` for an unknown signal.

Use `memory-seed branch status` before distinct feature or proposal work when you want Git history
to show clear branch-and-merge structure. It is read-only: it reports the current branch, dirty
state, upstream status, linked worktree count, recent merge-commit presence, and a recommendation.
It warns when feature-like work appears to be happening on an integration branch, but it never blocks
or creates branches automatically. For visible topology, work on a task branch/worktree and merge
back with `git merge --no-ff`.

Use `memory-seed worktree guard --agent <agent> --write-intent` before file edits in an agent
worktree workflow. It is read-only and reports whether the current checkout is the named agent's
namespace (`.codex/worktrees`, `.claude/worktrees`, `.gemini/worktrees`, `.cursor/worktrees`, or a
project override), a foreign namespace, the root checkout, an unmanaged worktree, or not a Git
worktree. Root checkout writes fail unless the operator passes `--allow-root-write`; unmanaged
worktrees warn by default unless `.memory-seed/project.yaml` sets `worktrees.unmanaged_write_policy`
to `block`.

Use `memory-seed session merge-branch --branch <branch>` to promote a task branch that contains
branch-local session entries or diagram sidecars: it dry-runs the fuse, merges with
`git merge --no-ff --no-commit`, applies the fuse, and commits in one step, so session entries land
in timestamp order without a separate manual fuse step. Fuse issues abort before the merge starts;
non-session conflicts leave the merge in progress for manual resolution.

The lower-level `memory-seed session fuse --branch <branch>` remains available for manually
inspected merges. It is a dry-run by default. Apply mode requires an in-progress
`git merge --no-ff --no-commit <branch>` and only imports validated branch-only entries whose YAML
`branch:` matches the source branch. Diagram sidecars are imported only when their parent entry
already exists on the base branch or is accepted for promotion in the same fuse.

From this repository checkout, run:

```powershell
python -m memory_seed.cli version
python -m memory_seed.cli doctor
python -m memory_seed.cli processes --json
python -m memory_seed.cli branch status
python -m memory_seed.cli shutdown --dry-run
python -m memory_seed.cli upgrade --dry-run --manager uv
python -m memory_seed.cli encoding check
python -m memory_seed.cli encoding repair --dry-run
python -m memory_seed.cli init --dry-run
python -m memory_seed.cli update --dry-run
python -m memory_seed.cli compact
python -m memory_seed.cli session merge-branch --branch <branch>
```

The `init` command copies only the reusable seed files into the current folder:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.memory-seed/agent-rules.md
.memory-seed/project-bootstrap.md
.memory-seed/archive/.gitkeep
.memory-seed/hooks/session-log-check.py
.memory-seed/hooks/memory-retrieval-check.py
.memory-seed/hooks/session-start-context.py
.memory-seed/hooks/prepare-commit-msg.py
.memory-seed/skills/index.md
.memory-seed/skills/end_of_turn.md
.memory-seed/skills/history_retrieval.md
.memory-seed/skills/memory_consolidation.md
.memory-seed/skills/memory_doctor.md
.memory-seed/skills/memory_hygiene.md
.memory-seed/skills/risk_signaling.md
.memory-seed/skills/session_logging.md
.memory-seed/skills/subproject_runtime.md
.memory-seed/sessions/.gitkeep
```

Optional profile skills are copied only when selected. It creates a minimal `.memory-seed/` control plane with reusable procedures, core skill templates, skill selection state, and empty session/archive anchors. Fresh projects are seeded but not yet bootstrapped. `init` does not create `.memory-seed/index.md` or `.memory-seed/policy.md`; the first agent bootstrap pass generates those files after scanning the project and asking targeted questions. The generated `index.md` is the rich project-orientation manifest, and `policy.md` contains behavioral constraints only.

It does not copy MCP server code or Python modules into the target project. Commands such as `memory-seed-mcp` and `memory-seed-mcp-validate` run from the installed or `uvx` package. The target project receives only the Markdown runtime files.

Use `--dry-run` to preview the files `init` would copy without changing files. If any reusable seed file already exists, plain `init` refuses to overwrite it and exits with an error. Use `--force` only when you intentionally want to back up and replace existing seed files.

When `--force` creates backups, Memory Seed adds `.memory-seed/backups/` to the target project's `.gitignore` to reduce the chance of committing replaced local memory files. `init --force` is a reinstall operation for the selected seed-file set, including files that were already on the current `memory-system-version`.

The `update` command refreshes routing files, reusable runtime procedure files, and generic skill templates by version, sourcing them **from the installed package** rather than from PyPI — upgrade the package first to get newer templates (see [Updating](#updating)). Before replacing stale reusable control-plane files, it backs them up under `.memory-seed/backups/<timestamp>/` and archives their old version under `.memory-seed/archive/<old-version>/` or `.memory-seed/archive/unknown-<timestamp>/` when the old version is missing. Generated local memory files such as `index.md`, `policy.md`, and sessions are preserved.

Use `update --dry-run` to list the reusable control-plane targets without writing files. Current behavior is conservative but broad: dry-run lists bundled seed paths rather than calculating which files are missing or version-mismatched. The real `update` command skips files already at the current `memory-system-version` or newer — so a stale installed tool never downgrades a project — and preserves existing `.memory-seed/` runtime files.

The `compact` command summarises recent session activity from the nearest runtime so an agent can identify durable facts to promote into `index.md`, `policy.md`, or skills. It reads the new month-grouped layout (`sessions/YYYY-MM/YYYY-MM-DD.md`, `sessions/YYYY-MM/YYYY-MM-DD/<user>.md`) and the legacy flat/day layouts (`sessions/YYYY-MM-DD.md`, `sessions/YYYY-MM-DD/<user>.md`):

```bash
memory-seed compact              # last 7 days (default)
memory-seed compact --days 30    # last 30 days
memory-seed compact --all        # all sessions
memory-seed compact --output summary.md  # write to file
```

The output is a structured Markdown report with session headings and full entry text. The CLI summarises; the agent (or user) decides what to promote. No files are modified automatically.

For upgrade preparation and safe package upgrades, Memory Seed can inspect package-owned processes,
shut down only matching processes after confirmation, and run the selected package-manager upgrade:

```bash
memory-seed processes
memory-seed processes --json
memory-seed shutdown --dry-run
memory-seed shutdown --dry-run --json
memory-seed shutdown
memory-seed shutdown --yes
memory-seed upgrade --dry-run --manager uv
memory-seed upgrade --manager uv
memory-seed upgrade --yes --manager uv
```

Shutdown defaults to `No` unless you confirm or pass `--yes`. Matching is conservative: generic
`python`, `uv`, `uvx`, and `pipx` processes are stopped only when their executable path or command
line clearly belongs to the target package. `upgrade` supports `--manager uv`, `--manager pipx`, and
`--manager pip`; if the manager cannot be detected safely in non-interactive mode, rerun with an
explicit `--manager`.

To opt into per-user session targets on a clone, configure a local user slug:

```bash
memory-seed user set jean
memory-seed user show
memory-seed session target
memory-seed session target --create
memory-seed user clear
```

The local selection is stored in `.memory-seed/local.yaml`, which Memory Seed adds to `.gitignore`. `MEMORY_SEED_USER` overrides the local file for one shell, and `memory-seed session target --user <slug>` overrides both. With no configured user, or with fewer than two registered participants, session targets use the grouped shared file (`sessions/YYYY-MM/YYYY-MM-DD.md`). With a configured user and at least two registered participants, new targets are `sessions/YYYY-MM/YYYY-MM-DD/<user>.md` and `--create` initializes file frontmatter with `schema_version: 2`, `session_date`, immutable `hash_id`, `user`, and `created_at`. An explicit `--user <slug>` override bypasses the participant gate for that command.

To migrate existing flat session files into the per-user layout, add a tracked participant registry to
`.memory-seed/project.yaml`:

```yaml
participants:
  - slug: jean
    initials: JN
    display_name: Jean
```

Then preview and apply the migration:

```bash
memory-seed migrate sessions-layout --dry-run
memory-seed migrate sessions-layout
```

The migration parses each legacy `sessions/YYYY-MM-DD.md` entry, maps its `user_initials` to a
participant slug, appends to `sessions/YYYY-MM/YYYY-MM-DD/<user>.md`, preserves existing `entry_id` values,
backs up the flat source under `.memory-seed/backups/<timestamp>/sessions/`, and removes the flat
source after a successful apply so permanent dual-read support does not create duplicate entry IDs.
It blocks rather than guessing when initials are missing, unknown, duplicated in the participant
registry, or when an existing per-user file already contains an incoming `entry_id`.

To reorganize historical flat/day files into the month-grouped layout, use the separate month-layout
migration:

```bash
memory-seed migrate sessions-month-layout --dry-run
memory-seed migrate sessions-month-layout
```

This preserves whether each source is shared-flat or per-user, moves old diagram sidecars from
`sessions/diagrams/YYYY-MM-DD.md` to `sessions/diagrams/YYYY-MM/YYYY-MM-DD.md`, backs up originals
before removal, and blocks duplicate `entry_id`/`hash_id` merges. It never runs during `init`,
`update`, hooks, MCP startup, or Memory Trace startup.

### Existing-Project Command Behavior

When run in a project that already has Memory Seed files:

- `memory-seed version` prints the bundled reusable control-plane version. It does not inspect the project.
- `memory-seed doctor` checks reusable seed files, reports missing files or `memory-system-version` mismatches, and separately reports incomplete bootstrap when generated `index.md` or `policy.md` is missing. It also warns (non-fatally) when a `.memory-seed/skills/*.md` runbook is not registered in `skills/index.md` (an orphan skill agents would never load), and when a `.memory-seed/` runtime exists but an entry-point file is foreign and carries no routing block (an orphaned runtime nothing points at).
- `memory-seed init --dry-run` lists the seed files it would copy and changes nothing, even if those files already exist.
- `memory-seed init` refuses to overwrite existing **owned** seed files unless `--force` is used. A pre-existing **foreign** entry-point file (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`.github/copilot-instructions.md` owned by another tool, i.e. no `memory-system-version` frontmatter) no longer blocks `init` — its content is preserved and a routing block is merged in instead.
- `memory-seed init --force` backs up and rewrites owned seed files. It still does **not** overwrite a foreign entry-point file — that is always merged, never clobbered.
- `memory-seed update` refreshes stale routing files, reusable runtime procedure files, and generic skill templates; archives replaced control-plane versions; and preserves generated local memory. For a **foreign** entry-point file it injects (or re-syncs in place) a marker-delimited `<!-- BEGIN memory-seed -->…<!-- END memory-seed -->` block that routes into `.memory-seed/`, leaving the host's own content untouched.
- `memory-seed compact` reads dated session logs from the nearest `.memory-seed/` runtime, including month-grouped and legacy flat/day layouts, with legacy `.AGENTS/` fallback. It prints a Markdown summary and writes only when `--output` is provided.
- `memory-seed user set/show/clear` manages a gitignored local user slug for opt-in per-user session files.
- `memory-seed topics list` shows the controlled topic vocabulary in `.memory-seed/topics.yaml` (deploy-once project-local; `update` never overwrites curation). `memory-seed topics check` validates it plus every entry's `topics:` usage - unknown/malformed/duplicate/collision slugs are errors, deprecated-use and more-than-3-per-entry are warnings. Meaningful entries carry 1-3 slugs; aliases resolve at read time, and `memory_search` accepts an alias-expanded opt-in `topics` filter.
- `memory-seed links check` validates session-memory integrity across both layouts: duplicate `entry_id`/`hash_id`, dangling `related_entries`/`related_memories`/`replaces`/`evolves` refs, forward-only lifecycle guards per edge kind (self-reference, postdating target, cycle - for both `replaces` and `evolves`), stored inverse keys (`authored-inverse-field`: `replaced_by`/`evolved_by` are read-time only), malformed `continuity:` blocks (unknown kind, missing `from`, `to` on removal, missing `to` on rename/migration), per-user-file frontmatter problems (filename↔frontmatter user/date mismatch, missing/malformed `hash_id`, unsupported `schema_version`), and lifecycle-edge **link sidecars** under `sessions/links/YYYY-MM/` (`orphan-link-sidecar`, `link-sidecar-date-mismatch`, `malformed-link-sidecar`; sidecar edges join the same dangling and forward-only guards). It names the offending file and value and exits non-zero on any issue, so it doubles as a CI gate; `doctor` surfaces a one-line summary pointing at it.
- `memory-seed migrate sessions-layout [--dry-run]` splits legacy flat session files into grouped per-user files using `.memory-seed/project.yaml` participants, backs up migrated sources, and refuses ambiguous or unsafe merges.
- `memory-seed migrate sessions-month-layout [--dry-run]` moves old flat/day session files and old diagram sidecars into grouped `YYYY-MM/` folders. It backs up sources, removes migrated originals after successful writes, and is never automatic.
- `memory-seed session fuse --branch <branch> [--base <ref>] [--apply]` dry-runs or applies branch-local session entries and sidecars into the current integration tree. It blocks missing or mismatched `branch:` metadata, missing/duplicate `entry_id` values, edits to existing entries or sidecars, non-chronological targets, and sidecars without a parent entry already on the base branch or accepted for promotion in the same fuse. `--apply` requires an in-progress merge and normalizes imported files to the grouped layout.
- `memory-seed session merge-branch --branch <branch> [--dry-run]` wraps the whole integration dance in one command: fuse dry-run gate, `git merge --no-ff --no-commit`, session-path reset to base content, fuse apply, stage, and merge commit. Fuse issues abort before the merge ever starts; non-session conflicts leave the merge in progress for manual resolution (never `merge --abort`); session files always land timestamp-sorted regardless of how git would have line-merged them. Requires a clean working tree.
- `memory-seed link suggest [--for <entry_id>] [--top-k N]` ranks older session entries to link from a target entry (default: the newest entry), skips the target and its already-linked entries, and prints a copy-pasteable `related_entries:` snippet. Candidates sharing rare `F:` file paths with the target get a rarity-weighted boost (hub files count ~nothing, absent `F:` is never penalized), with recorded `continuity:` renames alias-resolved transitively so pre-rename entries still overlap; shared files are shown as evidence. Read-only.
- `memory-seed link show <entry_id>` prints an entry's stored outbound `related_entries`, `replaces`/`evolves` edges, `continuity` artifact-lineage blocks, plus its computed inbound backlinks and `replaced_by`/`evolved_by` inverses, so the graph is bidirectional at read time without editing any historical entry. Read-only.
- `memory-seed link audit [--for <entry_id>] [--date YYYY-MM-DD]` finds entry pairs that share `F:` files or topics but carry no recorded edge - file overlap surfaces a candidate even when a `related_entries` link already exists (a lifecycle-upgrade hint), topic-only overlap is suppressed by any edge, and IDF weighting keeps hub files from dominating. `--date` scopes targets to one session (the end-of-turn sweep's input). Read-only.
- `memory-seed session append --title ... --user-initials ... --agent-type ... [--topics a,b] [--replaces id] [--evolves id] [--related id] [--body-file f]` appends a session entry with structure enforced: target resolution, heading timestamp (refusing out-of-order appends loudly), canonical deterministic `entry_id`, YAML shape, ref validation (fabricated or forward-pointing ids refused), controlled-topic resolution, and git branch auto-capture. The body prose passes through verbatim.
- `memory-seed session reorder --date YYYY-MM-DD [--apply]` repairs a misordered day's log as a pure block permutation - entries are stably re-sorted by heading timestamp with their bytes untouched. Dry-run by default.
- `memory-seed session entry-id --timestamp ... --title ... --user-initials ... --agent-type ...` computes the canonical deterministic entry id (also surfaced by a `memory_session_append` `dry_run` over MCP) - ids are a metadata hash, never invented by hand.
- `memory-seed hooks install` writes the `prepare-commit-msg` git shim (see Agent Hooks) into the git common dir; idempotent, and it never overwrites a hook it did not write.
- `memory-seed hooks status [--json]` reports whether the Memory-Entry trailer hook is current, missing, stale, broken, or blocked by a foreign hook.
- `memory-seed hooks repair` installs or refreshes only missing or Memory Seed-managed trailer hooks; foreign hooks are reported and left untouched.
- `memory-seed esr [--date YYYY-MM-DD] [--json]` prints the end-of-turn mechanical preflight report described under Agent Hooks; exit code reflects only hard integrity failures.
- `memory-seed processes [--json]` lists active package-owned Memory Seed processes.
- `memory-seed shutdown [--dry-run] [--yes] [--json]` previews or stops only matching package-owned Memory Seed processes after confirmation.
- `memory-seed upgrade [--dry-run] [--yes] [--manager uv|pipx|pip] [--json]` handles active package-owned processes, then runs the selected package-manager upgrade command.
- `memory-seed encoding check [path] [--json]` reports invalid UTF-8, UTF-8 BOMs, CRLF line endings, non-NFC text, likely mojibake markers, and implicit text-mode Python I/O in project-owned files.
- `memory-seed encoding repair [path] [--dry-run] [--json]` previews or repairs BOM, newline, and NFC drift with atomic writes and timestamped backups. Invalid UTF-8 and likely mojibake are blocked for manual review.
- `memory-trace` runs the review UI (bundled, `memory-seed[trace]`); without the extra it prints an install hint. The deprecated `memory-seed lense` alias was removed for the 2.20 release.
- `memory-seed session target [--create]` prints the active session log path and can create the file if needed.

Known behavior to understand: `update --dry-run` currently lists all control-plane targets, not only files that would actually change. `init --force` intentionally rewrites all bundled seed files and should be used as a reinstall command rather than a targeted refresh.

## Updating

Two separate things stay current, and they are not the same operation:

1. The installed **package** — the CLI, MCP server, and the seed templates bundled inside it.
2. Each **project's** `.memory-seed/` files — the seed files copied into a given repository.

`memory-seed update` copies seed files **from the package version currently installed or resolved**. It does not fetch from PyPI. So getting newer seed content into a project is a two-step process for persistent installs:

```powershell
# 1. Upgrade the tool (new code + new bundled seed templates)
uv tool upgrade memory-seed
# or, with pip:
python -m pip install --upgrade memory-seed

# 2. Propagate the new seed files into the project
memory-seed update --dry-run
memory-seed update
```

With `uvx`, pin to the latest to force the newest package before updating a project:

```powershell
uvx --from memory-seed@latest memory-seed update
```

A bare `uvx --from memory-seed memory-seed update` may serve a cached package version; use `@latest` to force the newest, or pin `==X.Y.Z` for reproducibility.

For the version distinction (`pip show memory-seed` reports the package version; `memory-seed version` reports the control-plane version), see [Python CLI](#python-cli).

## Text Encoding

Memory Seed writes project-owned text files as UTF-8 without BOM, with LF line endings and NFC Unicode normalization. `.editorconfig` and `.gitattributes` declare the repository defaults. Markdown memory files, YAML/TOML configuration, JSON metadata, logs, and generated text outputs should use explicit UTF-8 file I/O rather than platform defaults.

Use the shared `memory_seed.text_files` helpers for project-owned text and JSON writes. Important CLI and MCP output should remain understandable as plain text even when a terminal cannot render decorative Unicode.

Run the checker before release or after broad documentation edits:

```bash
memory-seed encoding check
memory-seed encoding check --json
memory-seed encoding repair --dry-run
```

The checker also flags non-NFC text and production Python calls that use text mode without an
explicit encoding. Tests, nested `.claude/worktrees/`, `.memory-seed/archive/`, and backup snapshots
are excluded from static or repair scope. Use
`# memory-seed: allow-implicit-text-io` only for a reviewed line where the platform default is
intentional.

`encoding repair` is explicit and backup-first. `--dry-run` previews changes. Applying it removes
UTF-8 BOMs, converts CRLF/bare-CR to LF, and normalizes Unicode to NFC using atomic replacement,
while preserving the original bytes under
`.memory-seed/backups/encoding/<timestamp>/`. Invalid UTF-8 and likely mojibake are never guessed at
or rewritten; the command reports them as blocked and exits non-zero.

## MCP Memory Search

Memory Seed also includes a lightweight MCP server that lets agents search local session memory through structured tool calls instead of shelling out to broad compact summaries.

**Auto-registration:** `memory-seed init` and `memory-seed update` automatically register `uvx --from memory-seed memory-seed-mcp --stdio` in each supported vendor's MCP config — `.mcp.json` at the project root (Claude Code), `.cursor/mcp.json` (Cursor), `.gemini/settings.json` (Gemini CLI), and `.codex/config.toml` (Codex CLI). No manual config is needed for projects initialised with Memory Seed. The `uvx --from` form is used so the command works regardless of whether `~/.local/bin` is on the agent's PATH.

> **Claude Code reads project-scope MCP servers from `.mcp.json`, not `.claude/settings.json`** — the latter is for hooks and permissions only. Versions 2.2.0–2.3.0 wrote the server into `.claude/settings.json`, where Claude Code silently ignored it; `memory-seed update` now writes `.mcp.json` and removes the dead entry. Restart Claude Code and approve the project server, then confirm with `claude mcp list`.

> **Codex loads a project `.codex/config.toml` only for *trusted* directories.** Memory Seed writes the `[mcp_servers.memory-seed]` table there, but Codex ignores it until you trust the project (Codex prompts on first use of a directory, or set trust in Codex settings). After trusting, confirm with `codex mcp list`. `memory-seed doctor` warns if Codex hooks are present without this registration. If you hand-wrote the `memory-seed` entry in a non-standard TOML form (dotted keys, an inline table, or a header with a trailing comment) and it is outdated, `memory-seed update` will not auto-migrate it — `memory-seed doctor` flags it as needing a manual fix instead of silently leaving stale settings in place.

If you are configuring the server manually, run it over stdio:

```powershell
uvx --from memory-seed memory-seed-mcp --stdio
```

Recommended MCP client command configuration:

```json
{
  "command": "uvx",
  "args": ["--from", "memory-seed", "memory-seed-mcp", "--stdio"]
}
```

For repeatable team or production usage, pin the package version:

```json
{
  "command": "uvx",
  "args": ["--from", "memory-seed==2.0.0", "memory-seed-mcp", "--stdio"]
}
```

If you installed Memory Seed globally, use the console script directly:

```json
{
  "command": "memory-seed-mcp",
  "args": ["--stdio"]
}
```

If the console script is not on `PATH`, use the module form from the active Python environment:

```json
{
  "command": "python",
  "args": ["-m", "memory_seed.mcp_server", "--stdio"]
}
```

The server exposes:

```text
memory_search(query, cwd=".", top_k=8, lambda_days=0.01, recency_enabled=true, recency_floor=0.15, semantic_enabled=true, user=null, date_from=null, date_to=null)
memory_get_chunk(chunk_id, cwd=".")
memory_link_suggest(cwd=".", entry_id=null, top_k=5)
memory_link_show(entry_id, cwd=".")
memory_session_append(title, body, user_initials, agent_type, cwd=".", agent_name=null, topics=null, related_entries=null, replaces=null, evolves=null, project_path=".", subproject_path=null, branch=null, auto_branch=true, timestamp=null, user=null, dry_run=false)
memory_session_integrate(branch, cwd=".", dry_run=false)
memory_topics_list(cwd=".")
memory_topic_inspect(topic, cwd=".")
memory_topics_check(cwd=".")
memory_branch_status(cwd=".")
memory_worktree_guard(agent_type, write_intent=false, allow_root_write=false, cwd=".")
memory_session_fuse_preview(branch, cwd=".", base="HEAD")
```

`memory_search` also accepts `granularity="entry"` by default or `granularity="section"` for narrower section-level results. It discovers session entries in `sessions/YYYY-MM/YYYY-MM-DD.md`, `sessions/YYYY-MM/YYYY-MM-DD/<user>.md`, and the legacy flat/day layouts. Entry granularity returns one coherent chunk per `##` session entry and normally uses the entry YAML `entry_id` as `chunk_id`, such as `ms-db2d715c` for legacy entries or `mse_0123456789abcdef` for new generated entries. Section granularity returns ids such as `ms-db2d715c#decisions/d1-use-draft-for-compact-decision-records` while preserving the parent `entry_id`.

`memory_search` returns JSON with source path, `path`, `session_date`, optional per-user `user`, optional `file_hash_id`, entry-level `related_entries`/`replaces`/`evolves`/`continuity`, line range, heading path, score fields, matched fields, matched terms, semantic status, entry metadata, granularity, and an excerpt. Each result also carries the **computed lifecycle status** (`replaced_by`, `evolved_by`) so a consumer sees "this decision was retired" or "newer work builds on this" at the moment of consumption, without a per-result `memory_get_chunk` round trip - additive read-only fields; ranking and result order are untouched. The `user`, `date_from`, and `date_to` filters are applied before ranking so `top_k` is selected from the filtered corpus. This is intended to be both agent-efficient and human-validatable.

The ranking engine stays local and CPU-friendly. MCP search uses a Model2Vec static embedding provider by default with the general-purpose `minishlab/potion-base-8M` model, combines semantic score with lexical and metadata scoring, then applies recency. If Model2Vec or the model cannot load or score a query, the server falls back to lexical, metadata, and recency ranking without failing the request. Use `--no-semantic` on `memory-seed-mcp --stdio` or `semantic_enabled=false` in `memory_search` to force fallback behavior.

`memory_link_suggest` and `memory_link_show` are read-only authoring-support tools and
`memory_session_append` is the write path: together they close the authoring loop that
`memory_search`/`memory_get_chunk` open on the read side. `memory_link_suggest` ranks older entries
to link (paste-ready `related_entries` for the entry just written, with the rarity-weighted `F:`
file-overlap boost and per-suggestion `shared_files` evidence), `memory_link_show` returns one
entry's graph node (outbound/inbound edges, supersession and evolution edges with their computed
inverses, continuity blocks, importance, linked-commit count), and `memory_session_append` appends
the entry itself through every structural guard (chronology, ref existence, forward-only
`replaces`/`evolves` edges, controlled topics, id collision, DRAFT body), stamping the heading
timestamp from the server clock; a `dry_run` returns the `entry_id`, timestamp, target path, and
`rendered` - the exact entry block a real call would append - without writing. They are routed through `history_retrieval.md`. `memory_session_append` is the only
sanctioned way to author an entry, so agents no longer hand-write session files.

`memory_topics_list`, `memory_topic_inspect`, and `memory_topics_check` are read-only topic-management
tools for agents. They expose the project topic index, resolve canonical slugs/aliases with entry
usage, and mirror `memory-seed topics check` validation without adding a write surface for the
project-curated `.memory-seed/topics.yaml` file.

`memory_branch_status`, `memory_worktree_guard`, and `memory_session_fuse_preview` are read-only
collaboration tools for LLM orchestrators, and `memory_session_integrate` is the write path that
applies a branch merge+fuse. The skill registry routes them through `agent_collaboration.md`, which
tells agents when to use the MCP guard/preview/integrate and when to fall back to CLI commands.
`memory_worktree_guard` classifies the current checkout as an owned worktree, foreign worktree, root
checkout, unmanaged worktree, or non-worktree for a named agent. Fuse preview reports planned
entries, planned sidecars, source removals, blockers, and the gated CLI apply command without
writing files. `memory_session_integrate` then applies that plan autonomously — the fuse gate, the
`--no-ff` merge, chronological session fusion, and the commit in one step — aborting and restoring a
clean tree on a non-session conflict and declining `pr` mode; the lower-level `session fuse --apply`
during an inspected `git merge --no-ff --no-commit` remains available for a hand-driven merge.

### Performance characteristics

`memory_search` is a relevance-and-recall tool, not a faster `grep`. A plain `grep` will out-scan it on raw exact-match throughput; the search wins instead on *semantic recall* over session history (surfacing relevant entries that lack the literal query words) and on *agent-token efficiency* (returning a small ranked set of self-contained chunks with stable `chunk_id`s, so an agent fetches only the one or two full entries worth reading). The two are complementary: use `memory_search` for "what did we decide and why," and `grep` for exact-string scans across the whole repo.

Per-query latency, measured in-process on this repo (81 chunks across the session logs), is roughly **30 ms**, of which about **22 ms is reading and parsing the session `.md` files** — the search re-reads and re-parses every discovered session document on each call, with no persistent chunk or vector cache — and the embed + cosine + rank step adds only a few ms on top. Cold start adds a one-time cost on the *first ever* call on a machine: the Model2Vec weights download into the local HuggingFace cache (tens of MB); afterwards the static model loads in a few ms. Because the static model has no transformer forward pass, the dominant cost is file I/O, so per-query time grows linearly with total session-log size rather than with model complexity.

When driving the server through an MCP client (Claude Code, Cursor, Gemini), the latency you actually perceive is dominated by one-time startup, not per-query work: spawning `uvx --from memory-seed memory-seed-mcp` resolves and may install the package into an ephemeral environment the first time the server launches in a session. Once the server is up, each `memory_search` is the ~30 ms compute above plus a small JSON-RPC round-trip. At current log sizes there is no need to optimize; should logs grow large enough that the ~22 ms parse cost becomes noticeable, caching parsed chunks and their vectors keyed by file modification time would remove most of the per-query cost.

Session entries should include a YAML metadata block with `entry_id`, `user_initials`, `agent_type`, `project_path`, and `subproject_path`. New generated `entry_id` values use deterministic 80-bit `mse_` IDs encoded as 16 lower-case Base32 characters; legacy `ms-` IDs remain valid and are not rewritten. Session entry YAML may include entry-level `related_entries` pointing at either old or new entry IDs. Session entry headings may include optional minute-level timestamps, such as `## 2026-05-19 20:42 - Durable memory consolidation`. New session filenames stay date-only inside their month folder; the opt-in per-user layout uses a month folder, date directory, and bare user slug (`sessions/YYYY-MM/YYYY-MM-DD/jean.md`). Timestamped headings are backward compatible with older untimed headings and are exposed as `entry_datetime` in MCP search results when present.

For human-validatable search behavior, see the fixture-style tests in `tests/test_mcp_server.py`. They assert that specific queries return expected dated session entries first and include enough evidence for manual review.

To manually validate the search-then-fetch workflow without configuring an agent client, run:

```powershell
uvx --from memory-seed memory-seed-mcp-validate "bootstrap mode check"
```

or, with a pinned package:

```powershell
uvx --from memory-seed==2.0.0 memory-seed-mcp-validate "bootstrap mode check"
```

If installed globally or running from this checkout:

```powershell
memory-seed-mcp-validate "bootstrap mode check"
python -m memory_seed.mcp_validate "bootstrap mode check"
```

The validation report shows the ranked search results, then fetches the top result by `chunk_id` and prints the exact source, heading, and full chunk text.

Ranking behavior should remain stable on `main`. If you want to experiment with ranking changes, use a separate branch and merge back only when fixture tests show a clear improvement.

## For Code Projects

When Memory Seed is planted into a software, library, or API project, agents will use [Semble](https://github.com/MinishLab/semble) for code search. Semble returns only the relevant code chunks, using ~98% fewer tokens than grep+read.

Install it once, globally:

```bash
claude mcp add semble -s user -- uvx --from "semble[mcp]" semble
```

During bootstrap, the agent adds a Code Search section to the project's `AGENTS.md` so all future agents, including sub-agents, can call `semble search` directly. No per-project setup is needed after that.

## Public Memory Hygiene

Memory Seed files are plain Markdown and may be committed with a project. Treat `.memory-seed` files as publishable unless the project is explicitly private.

Do not put secrets, credentials, tokens, private keys, sensitive account details, client confidential information, or unnecessary personal data into generated memory files or session logs.

## Publishing

This repository is configured for PyPI trusted publishing from GitHub Actions.

PyPI pending publisher settings should match:

```text
PyPI Project Name: memory-seed
Owner: jnl-tshi
Repository name: memory-seed
Workflow name: publish.yml
Environment name: pypi
```

The publish workflow lives at `.github/workflows/publish.yml`. It runs tests, builds the package with `uv build`, and publishes through PyPI's trusted publisher flow.

## Learn More

- [CHANGELOG](CHANGELOG.md) — what shipped in each release.
- [Active roadmap](docs/2_Todo/0_NEXT_STEPS.md) — the current implementation-run brief and stage plan.
- [Functionality audit](docs/3_Spec/functionality-audit.md) — the live normative inventory of every surface.
- [Graph-edge contract](docs/3_Spec/graph-edge-contract.md) — how decision-graph edges and metrics are defined.
- [Memory Trace](memory-trace/README.md) — the companion review UI's own README.
