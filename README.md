# Memory Seed

[![PyPI](https://img.shields.io/pypi/v/memory-seed.svg)](https://pypi.org/project/memory-seed/)
[![Python](https://img.shields.io/pypi/pyversions/memory-seed.svg)](https://pypi.org/project/memory-seed/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Publish to PyPI](https://github.com/jnl-tshi/memory-seed/actions/workflows/publish.yml/badge.svg)](https://github.com/jnl-tshi/memory-seed/actions/workflows/publish.yml)

Memory Seed is a portable local memory system for AI coding agents. It plants a small Markdown control plane into a project so agents can recover project purpose, conventions, risks, decisions, and recent work without depending on vendor-hosted memory.

It is built first for solo developers who move between Codex, Claude Code, Gemini CLI, and other file-reading agents. Teams can also use it to standardize local agent memory across repositories without introducing a database or hosted memory service.

## Demo

https://github.com/user-attachments/assets/b1c64d9e-4a67-4bc2-a030-d8ba7f17ccfe

[▶ Watch the 30-second demo](https://github.com/jnl-tshi/memory-seed/releases/download/v2.1.3/memory-seed-demo.mp4) if the player above does not load.

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

## See It Work

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

By default `memory-seed init` installs files for every supported agent. To keep a repo clean,
install only the agents you use:

```bash
memory-seed init --agents claude,codex     # only Claude + Codex artifacts
memory-seed init                            # interactive prompt on a terminal; all agents otherwise
```

`AGENTS.md`, the `.memory-seed/` runtime, and `.agents/` personas are always installed (they are
agent-agnostic). Only the agent-specific routing files (`CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md`) and per-agent hook/MCP configs are gated by the selection.
`codex` and `cursor` have no routing file — they read `AGENTS.md` natively.

The selection is persisted to `.memory-seed/project.yaml` (`agents:` list), which `doctor` and
`update` respect — so an unselected agent's files are never flagged missing or re-added. A project
with no `project.yaml` behaves as before (all agents). Reconfigure later:

```bash
memory-seed agents list           # show the selected agents
memory-seed agents add gemini     # install an agent's files
memory-seed agents remove gemini  # back up + remove an agent's files (foreign config preserved)
```

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

- `session-log-check.py` — after a turn, reminds the agent to append a session-log entry if none was written in the last 15 minutes, and warns if the day's entries are out of ascending time order.
- `memory-retrieval-check.py` — before substantive work, reminds the agent to use `memory_search` for topical recall and to read the newest session file directly for current state. Gated by an 8-hour marker file so it fires about once per working session.
- `session-start-context.py` — at session start, injects the newest session file's entries (path, all headings, and the most recent entry body) so the agent establishes current state by recency rather than semantic search. Fires once per session. Copilot CLI cannot run command hooks at session start, so it gets a static `prompt` hook with the same directive instead.

The hooks nudge; they never block. The scripts use Python 3.11+, which Memory Seed already requires.

## Reusable Seed Files

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.memory-seed/
  agent-rules.md
  project-bootstrap.md
  hooks/
    session-log-check.py
    memory-retrieval-check.py
  skills/
    index.md
    code_search.md
    data_architecture.md
    local_compilation.md
    memory_consolidation.md
    memory_doctor.md
    release_publishing.md
    security_triage.md
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

The current reusable control-plane version is `2.3`.

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
uvx --from memory-seed==2.0.0 memory-seed doctor
uvx --from memory-seed==2.0.0 memory-seed update --dry-run
```

If you are not using uv, install or upgrade the CLI with pip:

```powershell
python -m pip install --upgrade memory-seed
python -m pip show memory-seed
```

`python -m pip show memory-seed` reports the installed Python package version, such as `2.0.0`. `memory-seed version` reports the reusable control-plane version, currently `2.0`; it is not the package-version check.

To discover commands and flags, use `memory-seed help` (also shown when you run `memory-seed` with no command), `memory-seed -h`, or `memory-seed <command> -h` for a specific command.

From this repository checkout, run:

```powershell
python -m memory_seed.cli version
python -m memory_seed.cli doctor
python -m memory_seed.cli init --dry-run
python -m memory_seed.cli update --dry-run
python -m memory_seed.cli compact
```

The `init` command copies only the reusable seed files into the current folder:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.memory-seed/agent-rules.md
.memory-seed/project-bootstrap.md
.memory-seed/archive/.gitkeep
.memory-seed/skills/index.md
.memory-seed/skills/code_search.md
.memory-seed/skills/security_triage.md
.memory-seed/skills/data_architecture.md
.memory-seed/skills/local_compilation.md
.memory-seed/skills/memory_consolidation.md
.memory-seed/skills/memory_doctor.md
.memory-seed/skills/release_publishing.md
.memory-seed/sessions/.gitkeep
```

It creates a minimal `.memory-seed/` control plane with reusable procedures, generic skill templates, and empty session/archive anchors. Fresh projects are seeded but not yet bootstrapped. `init` does not create `.memory-seed/index.md` or `.memory-seed/policy.md`; the first agent bootstrap pass generates those files after scanning the project and asking targeted questions. The generated `index.md` is the rich project-orientation manifest, and `policy.md` contains behavioral constraints only.

It does not copy MCP server code or Python modules into the target project. Commands such as `memory-seed-mcp` and `memory-seed-mcp-validate` run from the installed or `uvx` package. The target project receives only the Markdown runtime files.

Use `--dry-run` to preview the files `init` would copy without changing files. If any reusable seed file already exists, plain `init` refuses to overwrite it and exits with an error. Use `--force` only when you intentionally want to back up and replace existing seed files.

When `--force` creates backups, Memory Seed adds `.memory-seed/backups/` to the target project's `.gitignore` to reduce the chance of committing replaced local memory files. `init --force` is a reinstall operation: it writes all bundled seed files, including files that were already on the current `memory-system-version`.

The `update` command refreshes routing files, reusable runtime procedure files, and generic skill templates by version, sourcing them **from the installed package** rather than from PyPI — upgrade the package first to get newer templates (see [Updating](#updating)). Before replacing stale reusable control-plane files, it backs them up under `.memory-seed/backups/<timestamp>/` and archives their old version under `.memory-seed/archive/<old-version>/` or `.memory-seed/archive/unknown-<timestamp>/` when the old version is missing. Generated local memory files such as `index.md`, `policy.md`, and sessions are preserved.

Use `update --dry-run` to list the reusable control-plane targets without writing files. Current behavior is conservative but broad: dry-run lists bundled seed paths rather than calculating which files are missing or version-mismatched. The real `update` command skips files already at the current `memory-system-version` or newer — so a stale installed tool never downgrades a project — and preserves existing `.memory-seed/` runtime files.

The `compact` command summarises recent session activity from the nearest runtime so an agent can identify durable facts to promote into `index.md`, `policy.md`, or skills:

```bash
memory-seed compact              # last 7 days (default)
memory-seed compact --days 30    # last 30 days
memory-seed compact --all        # all sessions
memory-seed compact --output summary.md  # write to file
```

The output is a structured Markdown report with session headings and full entry text. The CLI summarises; the agent (or user) decides what to promote. No files are modified automatically.

### Existing-Project Command Behavior

When run in a project that already has Memory Seed files:

- `memory-seed version` prints the bundled reusable control-plane version. It does not inspect the project.
- `memory-seed doctor` checks reusable seed files, reports missing files or `memory-system-version` mismatches, and separately reports incomplete bootstrap when generated `index.md` or `policy.md` is missing.
- `memory-seed init --dry-run` lists the seed files it would copy and changes nothing, even if those files already exist.
- `memory-seed init` refuses to overwrite existing seed files unless `--force` is used.
- `memory-seed init --force` backs up existing seed files and rewrites all bundled seed files.
- `memory-seed update` refreshes stale routing files, reusable runtime procedure files, and generic skill templates; archives replaced control-plane versions; and preserves generated local memory.
- `memory-seed compact` reads dated session logs from the nearest `.memory-seed/` runtime, with legacy `.AGENTS/` fallback, and prints a Markdown summary. It writes only when `--output` is provided.

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
memory_search(query, cwd=".", top_k=8, lambda_days=0.01, recency_enabled=true, recency_floor=0.15, semantic_enabled=true)
memory_get_chunk(chunk_id, cwd=".")
```

`memory_search` also accepts `granularity="entry"` by default or `granularity="section"` for narrower section-level results. Entry granularity returns one coherent chunk per `##` session entry and normally uses the entry YAML `entry_id` as `chunk_id`, such as `ms-db2d715c`. Section granularity returns ids such as `ms-db2d715c#decisions/d1-use-draft-for-compact-decision-records` while preserving the parent `entry_id`.

`memory_search` returns JSON with source path, line range, heading path, score fields, matched fields, matched terms, semantic status, entry metadata, granularity, and an excerpt. This is intended to be both agent-efficient and human-validatable.

The ranking engine stays local and CPU-friendly. MCP search uses a Model2Vec static embedding provider by default with the general-purpose `minishlab/potion-base-8M` model, combines semantic score with lexical and metadata scoring, then applies recency. If Model2Vec or the model cannot load or score a query, the server falls back to lexical, metadata, and recency ranking without failing the request. Use `--no-semantic` on `memory-seed-mcp --stdio` or `semantic_enabled=false` in `memory_search` to force fallback behavior.

### Performance characteristics

`memory_search` is a relevance-and-recall tool, not a faster `grep`. A plain `grep` will out-scan it on raw exact-match throughput; the search wins instead on *semantic recall* over session history (surfacing relevant entries that lack the literal query words) and on *agent-token efficiency* (returning a small ranked set of self-contained chunks with stable `chunk_id`s, so an agent fetches only the one or two full entries worth reading). The two are complementary: use `memory_search` for "what did we decide and why," and `grep` for exact-string scans across the whole repo.

Per-query latency, measured in-process on this repo (81 chunks across the session logs), is roughly **30 ms**, of which about **22 ms is reading and parsing the session `.md` files** — the search re-reads and re-parses every `sessions/*.md` on each call, with no persistent chunk or vector cache — and the embed + cosine + rank step adds only a few ms on top. Cold start adds a one-time cost on the *first ever* call on a machine: the Model2Vec weights download into the local HuggingFace cache (tens of MB); afterwards the static model loads in a few ms. Because the static model has no transformer forward pass, the dominant cost is file I/O, so per-query time grows linearly with total session-log size rather than with model complexity.

When driving the server through an MCP client (Claude Code, Cursor, Gemini), the latency you actually perceive is dominated by one-time startup, not per-query work: spawning `uvx --from memory-seed memory-seed-mcp` resolves and may install the package into an ephemeral environment the first time the server launches in a session. Once the server is up, each `memory_search` is the ~30 ms compute above plus a small JSON-RPC round-trip. At current log sizes there is no need to optimize; should logs grow large enough that the ~22 ms parse cost becomes noticeable, caching parsed chunks and their vectors keyed by file modification time would remove most of the per-query cost.

Session entries should include a YAML metadata block with `entry_id`, `user_initials`, `agent_type`, `project_path`, and `subproject_path`. Session entry headings may include optional minute-level timestamps, such as `## 2026-05-19 20:42 - Durable memory consolidation`. Session filenames stay date-only. Timestamped headings are backward compatible with older untimed headings and are exposed as `entry_datetime` in MCP search results when present.

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
