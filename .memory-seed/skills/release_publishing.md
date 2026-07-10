---
memory-system-version: 2.16
tags:
  - memory-seed
  - skill
  - release-publishing
---

# Release Publishing Skill

Use this skill when preparing or publishing a Memory Seed package release.

## Preconditions

- Package version in `pyproject.toml` matches the intended git tag.
- Control-plane version changes are documented when behavior changed materially.
- Prior reusable control-plane snapshots are archived under `.memory-seed/archive/<version>/`.
- Tests pass.
- README and CHANGELOG describe user-visible changes.

## Procedure

1. Run the full test suite.
2. Run `memory-seed doctor`.
3. Bump every version surface together: `pyproject.toml`, the control-plane `VERSION`, and the
   `memory-system-version:` frontmatter in the repo-root routing files (`AGENTS.md`, `CLAUDE.md`,
   `GEMINI.md`), their seed twins, `agent-rules.md` (live + seed), and the seeded skill files. The
   root routing files are the historical miss; a guard test asserts they match `get_version()`.
4. Fold the CHANGELOG: move `## Unreleased` content under a new `## <version> - <date>` heading
   and leave a standing **empty** `## Unreleased` header above it (a doc test requires the header
   to exist).
5. Archive the reusable control-plane snapshot under `.memory-seed/archive/<version>/` - an
   explicit operator step; no tooling creates it automatically.
6. Confirm package version and intended tag.
7. Commit changes intentionally.
8. Publish by creating a GitHub Release.
9. Do not use direct workflow dispatch for publishing.
10. Verify the release workflow completed. The `pypi` GitHub Environment holds the upload until
    the maintainer approves the gate; the PyPI push is irreversible once approved.

## Commands

```bash
python -m unittest discover -s tests
python -m memory_seed.cli doctor
gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."
```

## Output

- Version and tag.
- Verification commands and results.
- Release URL or blocker.
