---
memory-system-version: 2.15
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
3. Confirm package version and intended tag.
4. Commit changes intentionally.
5. Publish by creating a GitHub Release.
6. Do not use direct workflow dispatch for publishing.
7. Verify the release workflow completed.

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
