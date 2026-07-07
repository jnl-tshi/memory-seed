# UTF-8 Encoding Doctor And Static Check Plan

Status: Active proposal
Priority: Medium
Source: Split from `docs/2_Todo/completed/memory-seed-utf8-encoding-policy-phase-1.md` on 2026-07-07.
Scope: Add explicit validation and repair tooling for the UTF-8/LF/NFC text contract after the Phase 1 helper and documentation work.
Non-goals: Do not silently rewrite user files; do not repair suspected mojibake without an explicit command and backup path.
Dependencies: Phase 1 helper module `memory_seed.text_files`; final decision on whether mirrored `memory-trace encoding ...` commands should live in Trace or delegate to Memory Seed.
Acceptance criteria: `memory-seed encoding check` reports invalid UTF-8, UTF-8 BOM, CRLF line endings, and likely mojibake indicators; `memory-seed encoding repair --dry-run` previews changes; repair creates backups or requires a clean Git worktree; tests cover Markdown, JSON, YAML/TOML-like text, and append/repair cases.

## Rationale

Phase 1 established the policy and helper API. The remaining work is intentionally separated because checker and repair commands need conservative file-selection rules, clear backup behavior, and more test coverage than the quick policy pass.

## Proposed Work

1. Add an `encoding` CLI command group with `check` and `repair`.
2. Define the project-owned text file scan set.
3. Detect invalid UTF-8, BOM, CRLF, and known mojibake markers.
4. Keep repair opt-in, dry-run first, and backup-aware.
5. Add a lightweight static test that flags implicit text-mode reads/writes in production code, with documented exceptions.
6. Decide whether Memory Trace should expose its own command or call into Memory Seed's scanner.

## Verification

- `python -m unittest tests.test_text_files`
- Targeted CLI tests for `memory-seed encoding check`
- `python -m unittest discover -s tests`
