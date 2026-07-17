# Contributing to Memory Seed

Thanks for your interest. Memory Seed is maintained by a single maintainer; this document describes how
changes actually land, including the parts that differ from a large-team project.

## How changes land

1. **Work happens on branches** named `<agent-or-author>/<kind>/<topic>` (e.g. `claude/fix/entry-grammar`),
   never directly on `main`.
2. **Every change runs the full verification gate** — the `Verify` workflow (`.github/workflows/verify.yml`)
   runs the core suite, the Memory Trace suite, repository session-link integrity, and the React
   workspace type-check/build on every push and pull request.
3. **Merges happen at a green, tested stopping point.** Substantive changes also get a diff-level code
   review pass before merging.
4. **Releases are cut manually** and published to PyPI through OIDC Trusted Publishing with a manual
   approval gate. Contributors never need or touch publishing credentials.

## Code review, honestly stated

This is a solo-maintained project: there is no second human reviewer, so review is **self-review plus
automation** (the full test gate, CodeQL, Scorecard, session-integrity checks). We document that rather
than pretend otherwise. External pull requests do get maintainer review before merge.

## What to know before submitting

- **Tests are required.** New behaviour ships with tests; bug fixes ship with a regression test that
  fails before the fix. Run `python -m pytest tests` and (for Trace changes)
  `python -m unittest discover -s memory-trace/tests`.
- **Markdown is the source of truth** (Constitution Invariant #6): every cache, index, or projection must
  be rebuildable from the repository's Markdown. Changes that make a derived store authoritative will be
  declined.
- **Session history is append-only** (Invariant #2): corrections are new entries that point back, never
  edits to old ones.
- **Decision records:** durable decisions are logged in `.memory-seed/sessions/` using the DRAFT shape
  (`D:` decision and `R:` reason are mandatory). See `.memory-seed/skills/session_logging.md`.
- **Dependency hygiene:** plain `pip install memory-seed` stays web-framework-free; UI dependencies
  belong to the `trace` extra. New runtime dependencies need a strong case.
- **Security issues:** never via public issue — see [SECURITY.md](SECURITY.md).

## Development setup

```bash
pip install -e ".[trace]" pytest
python -m pytest tests
python -m unittest discover -s memory-trace/tests
```

The React workspace under `memory-trace/client/` uses Node 22: `npm ci && npm run typecheck && npm run build`.
Built assets are committed; CI fails if they drift from source.
