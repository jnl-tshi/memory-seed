# Memory Seed

Memory Seed is a portable local memory system for AI coding agents.

It provides a small set of plain Markdown control-plane files that can be planted into a new or existing project. During bootstrap, the seed generates project-specific operating memory so future agent sessions can recover the project's purpose, current state, conventions, risks, and recent decisions without depending on vendor-hosted memory.

## Goals

- Keep project memory local, inspectable, and portable.
- Support file-reading AI coding agents through predictable Markdown files.
- Route tool-specific entry files into one shared `.AGENTS/` memory core.
- Generate project-specific `index.md`, `context.md`, `style.md`, and session logs during bootstrap.
- Archive reusable control-plane versions while keeping generated project memory outside version archives.

## Reusable Seed Files

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.AGENTS/
  agent-rules.md
  project-bootstrap.md
```

## Generated Per-Project Files

```text
.AGENTS/
  index.md
  context.md
  style.md
  sessions/
```

## Current Version

The current reusable control-plane version is `1.4`.

Archived reusable versions are stored under `.AGENTS/archive/<version>/`.

## Python CLI

Memory Seed includes a small Python CLI.

From this repository, run:

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
.AGENTS/agent-rules.md
.AGENTS/project-bootstrap.md
```

It does not copy generated project memory such as `.AGENTS/context.md`, `.AGENTS/index.md`, `.AGENTS/style.md`, `.AGENTS/sessions/`, or `.AGENTS/archive/`.

Use `--dry-run` to preview the files `init` would copy without changing files. If any reusable seed file already exists, plain `init` refuses to overwrite it and exits with an error. Use `--force` only when you intentionally want to back up and replace existing seed files.

When `--force` creates backups, Memory Seed adds `.AGENTS/backups/` to the target project's `.gitignore` to reduce the chance of committing replaced local memory files. `init --force` is a reinstall operation: it writes all bundled seed files, including files that were already on the current `memory-system-version`.

The `update` command refreshes only the reusable control-plane files in an existing project. It uses each file's `memory-system-version` YAML field to decide whether that file is current. It backs up replaced control-plane files under `.AGENTS/backups/<timestamp>/`, restores any missing reusable seed files, skips files already on the current control-plane version, and does not change generated project memory such as `.AGENTS/context.md`, `.AGENTS/index.md`, `.AGENTS/style.md`, or `.AGENTS/sessions/`.

Use `update --dry-run` to list the reusable control-plane targets without writing files. Current behavior is conservative but broad: dry-run lists all five control-plane paths rather than calculating which files are missing or version-mismatched. The real `update` command skips files that already have the current `memory-system-version`.

The `compact` command summarises recent session activity so an agent can identify durable facts to promote into `context.md`, `index.md`, and `style.md`:

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
- `memory-seed doctor` checks only the five reusable control-plane files and reports missing files or `memory-system-version` mismatches. It does not check generated operating memory files.
- `memory-seed init --dry-run` lists the five seed files it would copy and changes nothing, even if those files already exist.
- `memory-seed init` refuses to overwrite existing seed files unless `--force` is used.
- `memory-seed init --force` backs up existing seed files and rewrites all five bundled seed files. It does not generate operating memory files.
- `memory-seed update` skips current-version control-plane files, backs up and replaces stale files, restores missing files, and leaves generated project memory untouched.
- `memory-seed compact` reads dated session logs and prints a Markdown summary. It writes only when `--output` is provided.

Known behavior to understand: `update --dry-run` currently lists all control-plane targets, not only files that would actually change. `init --force` intentionally rewrites all bundled seed files and should be used as a reinstall command rather than a targeted refresh.

## MCP Memory Search

Memory Seed also includes a lightweight MCP server that lets agents search local session memory through structured tool calls instead of shelling out to broad compact summaries.

Run it over stdio:

```powershell
memory-seed-mcp --stdio
```

Example MCP client command configuration:

```json
{
  "command": "memory-seed-mcp",
  "args": ["--stdio"]
}
```

If the console script is not on `PATH`, use the module form from the project environment:

```json
{
  "command": "python",
  "args": ["-m", "memory_seed.mcp_server", "--stdio"]
}
```

The server exposes:

```text
memory_search(query, cwd=".", top_k=8, today=None, lambda_days=0.01, recency_enabled=true, recency_floor=0.15)
memory_get_chunk(chunk_id, cwd=".")
```

`memory_search` returns JSON with source path, line range, heading path, score fields, matched fields, matched terms, and an excerpt. This is intended to be both agent-efficient and human-validatable.

The ranking engine remains local and dependency-light. It uses deterministic lexical scoring and recency math by default; optional semantic embedding support stays in the importable Python core and is not required to run the MCP server.

For human-validatable search behavior, see the fixture-style tests in `tests/test_mcp_server.py`. They assert that specific queries return expected dated session entries first and include enough evidence for manual review.

To manually validate the search-then-fetch workflow without configuring an agent client, run:

```powershell
memory-seed-mcp-validate "bootstrap mode check"
```

or:

```powershell
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

During bootstrap, the agent adds a Code Search section to the project's `AGENTS.md` so all future agents — including sub-agents — can call `semble search` directly. No per-project setup is needed after that.

## Public Memory Hygiene

Memory Seed files are plain Markdown and may be committed with a project. Treat `.AGENTS` files as publishable unless the project is explicitly private.

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
