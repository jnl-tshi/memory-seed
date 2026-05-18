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

Use `--dry-run` to preview without changing files. Use `--force` only when you intentionally want to back up and replace existing seed files.

When `--force` creates backups, Memory Seed adds `.AGENTS/backups/` to the target project's `.gitignore` to reduce the chance of committing replaced local memory files.

The `update` command refreshes only the reusable control-plane files in an existing project. It uses each file's `memory-system-version` YAML field to decide whether that file is current. It backs up replaced control-plane files under `.AGENTS/backups/<timestamp>/`, restores any missing reusable seed files, skips files already on the current control-plane version, and does not change generated project memory such as `.AGENTS/context.md`, `.AGENTS/index.md`, `.AGENTS/style.md`, or `.AGENTS/sessions/`.

The `compact` command summarises recent session activity so an agent can identify durable facts to promote into `context.md`, `index.md`, and `style.md`:

```bash
memory-seed compact              # last 7 days (default)
memory-seed compact --days 30    # last 30 days
memory-seed compact --all        # all sessions
memory-seed compact --output summary.md  # write to file
```

The output is a structured Markdown report with session headings and full entry text. The CLI summarises; the agent (or user) decides what to promote. No files are modified automatically.

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
