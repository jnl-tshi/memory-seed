# UTF-8 Encoding Doctor And Static Check Plan

Status: COMPLETED 2026-07-08 - check, repair, static implicit-I/O enforcement, and doctor summary
are implemented in unreleased changes.
Priority: Medium
Source: Split from `docs/2_Todo/completed/memory-seed-utf8-encoding-policy-phase-1.md` on 2026-07-07.
Scope: Add explicit validation and repair tooling for the UTF-8/LF/NFC text contract after the Phase 1 helper and documentation work.
Non-goals: Do not silently rewrite user files; do not repair suspected mojibake without an explicit command and backup path.
Dependencies: Phase 1 helper module `memory_seed.text_files`. Encoding commands remain owned by
Memory Seed; Memory Trace depends on the core package and does not duplicate this policy surface.
Acceptance criteria: `memory-seed encoding check` reports invalid UTF-8, UTF-8 BOM, CRLF line endings, and likely mojibake indicators; `memory-seed encoding repair --dry-run` previews changes; repair creates backups or requires a clean Git worktree; tests cover Markdown, JSON, YAML/TOML-like text, and append/repair cases.

Implemented:

- `encoding check` reports invalid UTF-8, BOM, CRLF, non-NFC text, likely mojibake, and implicit
  production Python text I/O.
- `encoding repair --dry-run` previews safe changes; apply mode uses atomic replacement and stores
  original bytes under `.memory-seed/backups/encoding/<timestamp>/`.
- Invalid UTF-8 and likely mojibake block automatic repair and require manual review.
- Nested `.claude/worktrees`, `.memory-seed/archive`, backups, and tests are excluded as appropriate.
- `doctor` provides a non-fatal summary pointing to `memory-seed encoding check`.
- `# memory-seed: allow-implicit-text-io` documents reviewed static-check exceptions.

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
